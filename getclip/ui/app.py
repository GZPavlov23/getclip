import os
import threading

import ttkbootstrap as tb
from ttkbootstrap.constants import *

from getclip.core.config import APP_NAME, DEFAULT_OUTPUT_DIR
from getclip.core.models import DownloadJob, MediaFormat, Quality, QueueItem, QueueStatus
from getclip.core.url_utils import detect_source_type, SOURCE_HINTS
from getclip.services.downloader import run_download, fetch_preview
from getclip.ui.thumbnail import load_thumbnail

PREVIEW_DEBOUNCE_MS = 700


class GetClipApp:
    def __init__(self, root: tb.Window):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("800x780")
        self.root.minsize(760, 740)

        self.url_var = tb.StringVar()
        self.hint_var = tb.StringVar(value="")
        self.preview_title_var = tb.StringVar(value="")
        self.format_var = tb.StringVar(value=MediaFormat.MP4.value)
        self.quality_var = tb.StringVar(value=Quality.BEST.value)
        self.trim_var = tb.BooleanVar(value=False)
        self.start_var = tb.StringVar()
        self.end_var = tb.StringVar()
        self.output_dir_var = tb.StringVar(value=DEFAULT_OUTPUT_DIR)
        self.status_var = tb.StringVar(value="Idle")

        self._debounce_id = None
        self._thumbnail_image = None
        self.queue: list[QueueItem] = []
        self._queue_running = False
        self._busy = False

        self._build_layout()
        self.url_var.trace_add("write", self._on_url_changed)

    def _build_layout(self):
        header = tb.Frame(self.root, padding=(24, 20, 24, 10))
        header.pack(fill=X)
        tb.Label(header, text="GetClip", font=("", 22, "bold")).pack(anchor=W)
        tb.Label(
            header, text="Download YouTube & Twitch clips, fast.", bootstyle=SECONDARY,
        ).pack(anchor=W)

        body = tb.Frame(self.root, padding=(24, 10, 24, 0))
        body.pack(fill=BOTH, expand=YES)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(2, weight=1)

        self._build_preview_card(body)
        self._build_source_card(body)
        self._build_trim_card(body)
        self._build_queue_card(body)
        self._build_footer()

    def _build_preview_card(self, parent):
        card = tb.Frame(parent, padding=(0, 0, 0, 10))
        card.grid(row=0, column=0, columnspan=2, sticky=NSEW)

        self.thumbnail_label = tb.Label(card)
        self.thumbnail_label.pack(side=LEFT, padx=(0, 12))

        tb.Label(
            card, textvariable=self.preview_title_var, font=("", 11), wraplength=380, justify=LEFT,
        ).pack(side=LEFT, anchor=W)

    def _build_source_card(self, parent):
        card = tb.Labelframe(parent, text="Source", padding=16, bootstyle=SECONDARY)
        card.grid(row=1, column=0, sticky=NSEW, padx=(0, 10))

        tb.Label(card, text="URL").pack(anchor=W)
        tb.Entry(card, textvariable=self.url_var).pack(fill=X, pady=(4, 6))
        tb.Label(card, textvariable=self.hint_var, bootstyle="info").pack(anchor=W, pady=(0, 16))

        tb.Label(card, text="Format").pack(anchor=W)
        format_row = tb.Frame(card)
        format_row.pack(fill=X, pady=(4, 16))
        tb.Radiobutton(
            format_row, text="MP4", variable=self.format_var,
            value=MediaFormat.MP4.value, bootstyle="toolbutton",
        ).pack(side=LEFT, padx=(0, 6))
        tb.Radiobutton(
            format_row, text="MP3", variable=self.format_var,
            value=MediaFormat.MP3.value, bootstyle="toolbutton",
        ).pack(side=LEFT)

        tb.Label(card, text="Quality").pack(anchor=W)
        tb.Combobox(
            card, textvariable=self.quality_var, state="readonly",
            values=[q.value for q in Quality],
        ).pack(fill=X, pady=(4, 16))

        self.add_queue_btn = tb.Button(
            card, text="+ Add to queue instead", bootstyle="link", command=self._add_to_queue,
        )
        self.add_queue_btn.pack(anchor=W)

    def _build_trim_card(self, parent):
        card = tb.Labelframe(parent, text="Trim & Save", padding=16, bootstyle=SECONDARY)
        card.grid(row=1, column=1, sticky=NSEW, padx=(10, 0))

        tb.Checkbutton(
            card, text="Trim to timestamp range", variable=self.trim_var,
            bootstyle="round-toggle",
        ).pack(anchor=W, pady=(0, 14))

        time_row = tb.Frame(card)
        time_row.pack(fill=X, pady=(0, 16))
        tb.Label(time_row, text="Start").pack(side=LEFT)
        tb.Entry(time_row, textvariable=self.start_var, width=9).pack(side=LEFT, padx=(6, 16))
        tb.Label(time_row, text="End").pack(side=LEFT)
        tb.Entry(time_row, textvariable=self.end_var, width=9).pack(side=LEFT, padx=6)

        tb.Label(card, text="Save to").pack(anchor=W)
        out_row = tb.Frame(card)
        out_row.pack(fill=X, pady=(4, 0))
        tb.Entry(out_row, textvariable=self.output_dir_var).pack(side=LEFT, fill=X, expand=YES, padx=(0, 6))
        tb.Button(
            out_row, text="Browse", command=self._choose_output_dir, bootstyle="secondary-outline",
        ).pack(side=LEFT)

    def _build_queue_card(self, parent):
        card = tb.Labelframe(parent, text="Queue (optional — for batches)", padding=16, bootstyle=SECONDARY)
        card.grid(row=2, column=0, columnspan=2, sticky=NSEW, pady=(16, 0))
        card.rowconfigure(0, weight=1)
        card.columnconfigure(0, weight=1)

        self.queue_tree = tb.Treeview(
            card, columns=("label", "format", "status"), show="headings", height=4,
        )
        self.queue_tree.heading("label", text="Video")
        self.queue_tree.heading("format", text="Format")
        self.queue_tree.heading("status", text="Status")
        self.queue_tree.column("label", width=380)
        self.queue_tree.column("format", width=80, anchor=CENTER)
        self.queue_tree.column("status", width=120, anchor=CENTER)
        self.queue_tree.grid(row=0, column=0, sticky=NSEW, pady=(0, 12))

        self.queue_tree.tag_configure("downloading", foreground="#3ba7e0")
        self.queue_tree.tag_configure("done", foreground="#4cbb6c")
        self.queue_tree.tag_configure("failed", foreground="#e0555b")

        self.start_queue_btn = tb.Button(
            card, text="Start Queue", bootstyle="secondary-outline", command=self._start_queue,
        )
        self.start_queue_btn.grid(row=1, column=0, sticky=EW, ipady=4)

    def _build_footer(self):
        footer = tb.Frame(self.root, padding=24)
        footer.pack(fill=X, side=BOTTOM)

        self.download_now_btn = tb.Button(
            footer, text="Download Now", bootstyle=SUCCESS, command=self._download_now,
        )
        self.download_now_btn.pack(fill=X, pady=(0, 10), ipady=8)

        self.progress = tb.Progressbar(footer, mode="determinate", maximum=100, bootstyle="info-striped")
        self.progress.pack(fill=X, pady=(0, 6))

        tb.Label(footer, textvariable=self.status_var, bootstyle=SECONDARY).pack(anchor=W)

    def _choose_output_dir(self):
        chosen = tb.filedialog.askdirectory()
        if chosen:
            self.output_dir_var.set(chosen)

    def _on_url_changed(self, *args):
        source = detect_source_type(self.url_var.get())
        self.hint_var.set(SOURCE_HINTS[source])

        if self._debounce_id is not None:
            self.root.after_cancel(self._debounce_id)

        self.preview_title_var.set("")
        self.thumbnail_label.configure(image="")

        url = self.url_var.get().strip()
        if not url:
            return

        self._debounce_id = self.root.after(PREVIEW_DEBOUNCE_MS, lambda: self._start_preview_fetch(url))

    def _start_preview_fetch(self, url: str):
        self.preview_title_var.set("Loading preview...")
        thread = threading.Thread(target=self._fetch_preview_in_background, args=(url,), daemon=True)
        thread.start()

    def _fetch_preview_in_background(self, url: str):
        try:
            preview = fetch_preview(url)
            thumbnail_image = None
            if preview.thumbnail_url:
                thumbnail_image = load_thumbnail(preview.thumbnail_url, max_width=180)
            self.root.after(0, lambda: self._show_preview(preview.title, thumbnail_image))
        except Exception:
            self.root.after(0, lambda: self.preview_title_var.set(""))

    def _show_preview(self, title: str, thumbnail_image):
        if self.url_var.get().strip() == "":
            return

        self.preview_title_var.set(title)

        if thumbnail_image is not None:
            self._thumbnail_image = thumbnail_image
            self.thumbnail_label.configure(image=self._thumbnail_image)

    def _add_to_queue(self):
        job = self._build_job_from_inputs()
        if job is None:
            return

        self.queue.append(QueueItem(job=job, label=self._current_label(job)))
        self._refresh_queue_view()
        self.url_var.set("")

    def _download_now(self):
        if self._busy:
            tb.dialogs.Messagebox.show_info("Wait for the current download to finish first.", "Busy")
            return

        job = self._build_job_from_inputs()
        if job is None:
            return

        label = self._current_label(job)
        self.url_var.set("")

        self._set_busy(True)
        self.status_var.set(f"Starting: {label}")
        self.progress["value"] = 0

        thread = threading.Thread(target=self._run_single_download, args=(job, label), daemon=True)
        thread.start()

    def _run_single_download(self, job: DownloadJob, label: str):
        try:
            run_download(job, on_progress=lambda d: self._handle_single_progress(label, d))
            self.root.after(0, lambda: self._on_single_download_finished(label))
        except Exception as e:
            self.root.after(0, lambda: self._on_single_download_failed(str(e)))

    def _handle_single_progress(self, label: str, progress_data: dict):
        if progress_data["status"] == "downloading":
            percent_text = progress_data.get("_percent_str", "0%").strip().replace("%", "")
            try:
                percent = float(percent_text)
            except ValueError:
                percent = 0.0
            self.root.after(0, lambda p=percent: self._update_single_progress(label, p))
        elif progress_data["status"] == "finished":
            self.root.after(0, lambda: self.status_var.set(f"Converting: {label}"))

    def _update_single_progress(self, label: str, percent: float):
        self.progress["value"] = percent
        self.status_var.set(f"{label} — {percent:.0f}%")

    def _on_single_download_finished(self, label: str):
        self.progress["value"] = 100
        self.status_var.set(f"Done: {label}")
        self._set_busy(False)

    def _on_single_download_failed(self, error_message: str):
        self.status_var.set("Error")
        self._set_busy(False)
        tb.dialogs.Messagebox.show_error(error_message, "Download failed")

    def _set_busy(self, busy: bool):
        self._busy = busy
        state = DISABLED if busy else NORMAL
        self.download_now_btn.configure(state=state)
        self.start_queue_btn.configure(state=state)

    def _current_label(self, job: DownloadJob) -> str:
        label = self.preview_title_var.get().strip() or job.url
        if len(label) > 55:
            label = label[:52] + "..."
        return label

    def _refresh_queue_view(self):
        self.queue_tree.delete(*self.queue_tree.get_children())
        for index, item in enumerate(self.queue):
            self.queue_tree.insert(
                "", END, iid=str(index),
                values=(item.label, item.job.media_format.value.upper(), item.status.value),
                tags=(item.status.name.lower(),),
            )

    def _build_job_from_inputs(self) -> DownloadJob | None:
        url = self.url_var.get().strip()
        if not url:
            tb.dialogs.Messagebox.show_error("Paste a URL first.", "Missing URL")
            return None

        os.makedirs(self.output_dir_var.get(), exist_ok=True)

        start_seconds = None
        end_seconds = None
        if self.trim_var.get():
            start_seconds = self._parse_time(self.start_var.get())
            end_seconds = self._parse_time(self.end_var.get())
            if start_seconds is None or end_seconds is None:
                tb.dialogs.Messagebox.show_error("Enter both a start and end time.", "Missing timestamps")
                return None

        return DownloadJob(
            url=url,
            output_dir=self.output_dir_var.get(),
            media_format=MediaFormat(self.format_var.get()),
            quality=Quality(self.quality_var.get()),
            start_seconds=start_seconds,
            end_seconds=end_seconds,
        )

    @staticmethod
    def _parse_time(value: str) -> int | None:
        value = value.strip()
        if not value:
            return None
        if value.isdigit():
            return int(value)
        parts = [int(p) for p in value.split(":")]
        seconds = 0
        for part in parts:
            seconds = seconds * 60 + part
        return seconds

    def _start_queue(self):
        if self._busy:
            tb.dialogs.Messagebox.show_info("Wait for the current download to finish first.", "Busy")
            return

        pending = [item for item in self.queue if item.status == QueueStatus.PENDING]
        if not pending:
            tb.dialogs.Messagebox.show_info("Add at least one video to the queue first.", "Queue is empty")
            return

        self._set_busy(True)
        thread = threading.Thread(target=self._process_queue, daemon=True)
        thread.start()

    def _process_queue(self):
        total = len([item for item in self.queue if item.status == QueueStatus.PENDING])
        completed = 0

        for item in self.queue:
            if item.status != QueueStatus.PENDING:
                continue

            completed += 1
            self.root.after(0, lambda i=item, c=completed, t=total: self._mark_item_downloading(i, c, t))

            try:
                run_download(
                    item.job,
                    on_progress=lambda d, i=item, c=completed, t=total: self._handle_queue_progress(i, c, t, d),
                )
                self.root.after(0, lambda i=item: self._mark_item_done(i))
            except Exception as e:
                self.root.after(0, lambda i=item, err=str(e): self._mark_item_failed(i, err))

        self.root.after(0, self._on_queue_finished)

    def _mark_item_downloading(self, item: QueueItem, completed: int, total: int):
        item.status = QueueStatus.DOWNLOADING
        self._refresh_queue_view()
        self.progress["value"] = 0
        self.status_var.set(f"[{completed}/{total}] Starting: {item.label}")

    def _handle_queue_progress(self, item: QueueItem, completed: int, total: int, progress_data: dict):
        if progress_data["status"] == "downloading":
            percent_text = progress_data.get("_percent_str", "0%").strip().replace("%", "")
            try:
                percent = float(percent_text)
            except ValueError:
                percent = 0.0
            self.root.after(0, lambda p=percent: self._update_progress(p, item.label, completed, total))
        elif progress_data["status"] == "finished":
            self.root.after(0, lambda: self.status_var.set(f"[{completed}/{total}] Converting: {item.label}"))

    def _update_progress(self, percent: float, label: str, completed: int, total: int):
        self.progress["value"] = percent
        self.status_var.set(f"[{completed}/{total}] {label} — {percent:.0f}%")

    def _mark_item_done(self, item: QueueItem):
        item.status = QueueStatus.DONE
        self._refresh_queue_view()

    def _mark_item_failed(self, item: QueueItem, error: str):
        item.status = QueueStatus.FAILED
        item.error = error
        self._refresh_queue_view()

    def _on_queue_finished(self):
        self._set_busy(False)
        self.progress["value"] = 100

        failed = [item for item in self.queue if item.status == QueueStatus.FAILED]
        if failed:
            self.status_var.set(f"Queue finished with {len(failed)} error(s)")
            names = "\n".join(item.label for item in failed)
            tb.dialogs.Messagebox.show_error(f"These failed to download:\n\n{names}", "Some downloads failed")
        else:
            self.status_var.set("Queue finished")


def main():
    root = tb.Window(themename="darkly")
    GetClipApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()