import os
import threading

import ttkbootstrap as tb
from ttkbootstrap.constants import *

from getclip.core.config import APP_NAME, DEFAULT_OUTPUT_DIR
from getclip.core.models import DownloadJob, MediaFormat, Quality
from getclip.services.downloader import run_download


class GetClipApp:
    def __init__(self, root: tb.Window):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("720x520")
        self.root.minsize(680, 480)

        self.url_var = tb.StringVar()
        self.format_var = tb.StringVar(value=MediaFormat.MP4.value)
        self.quality_var = tb.StringVar(value=Quality.BEST.value)
        self.trim_var = tb.BooleanVar(value=False)
        self.start_var = tb.StringVar()
        self.end_var = tb.StringVar()
        self.output_dir_var = tb.StringVar(value=DEFAULT_OUTPUT_DIR)
        self.status_var = tb.StringVar(value="Idle")

        self._build_layout()

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
        body.rowconfigure(0, weight=1)

        self._build_source_card(body)
        self._build_trim_card(body)
        self._build_footer()

    def _build_source_card(self, parent):
        card = tb.Labelframe(parent, text="Source", padding=16, bootstyle=SECONDARY)
        card.grid(row=0, column=0, sticky=NSEW, padx=(0, 10))

        tb.Label(card, text="URL").pack(anchor=W)
        tb.Entry(card, textvariable=self.url_var).pack(fill=X, pady=(4, 16))

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
        ).pack(fill=X, pady=(4, 0))

    def _build_trim_card(self, parent):
        card = tb.Labelframe(parent, text="Trim & Save", padding=16, bootstyle=SECONDARY)
        card.grid(row=0, column=1, sticky=NSEW, padx=(10, 0))

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

    def _build_footer(self):
        footer = tb.Frame(self.root, padding=24)
        footer.pack(fill=X, side=BOTTOM)

        self.download_btn = tb.Button(
            footer, text="Download", bootstyle=INFO, command=self._on_download_clicked,
        )
        self.download_btn.pack(fill=X, pady=(0, 10), ipady=6)

        self.progress = tb.Progressbar(footer, mode="determinate", maximum=100, bootstyle="info-striped")
        self.progress.pack(fill=X, pady=(0, 6))

        tb.Label(footer, textvariable=self.status_var, bootstyle=SECONDARY).pack(anchor=W)

    def _choose_output_dir(self):
        chosen = tb.filedialog.askdirectory()
        if chosen:
            self.output_dir_var.set(chosen)

    def _on_download_clicked(self):
        job = self._build_job_from_inputs()
        if job is None:
            return

        self.download_btn.configure(state=DISABLED)
        self.status_var.set("Starting...")
        self.progress["value"] = 0

        thread = threading.Thread(target=self._run_download_in_background, args=(job,), daemon=True)
        thread.start()

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

    def _run_download_in_background(self, job: DownloadJob):
        try:
            run_download(job, on_progress=self._handle_progress)
            self.root.after(0, self._on_download_finished)
        except Exception as e:
            self.root.after(0, lambda: self._on_download_failed(str(e)))

    def _handle_progress(self, progress_data: dict):
        if progress_data["status"] == "downloading":
            percent_text = progress_data.get("_percent_str", "0%").strip().replace("%", "")
            try:
                percent = float(percent_text)
            except ValueError:
                percent = 0.0
            self.root.after(0, lambda: self._update_progress(percent))
        elif progress_data["status"] == "finished":
            self.root.after(0, lambda: self.status_var.set("Converting..."))

    def _update_progress(self, percent: float):
        self.progress["value"] = percent
        self.status_var.set(f"Downloading... {percent:.0f}%")

    def _on_download_finished(self):
        self.progress["value"] = 100
        self.status_var.set("Done!")
        self.download_btn.configure(state=NORMAL)

    def _on_download_failed(self, error_message: str):
        self.status_var.set("Error")
        self.download_btn.configure(state=NORMAL)
        tb.dialogs.Messagebox.show_error(error_message, "Download failed")


def main():
    root = tb.Window(themename="darkly")
    GetClipApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()