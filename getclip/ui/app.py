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
        self.root.geometry("600x600")

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
        container = tb.Frame(self.root, padding=16)
        container.pack(fill=BOTH, expand=YES)

        tb.Label(container, text="Video / Clip / VOD URL", font=("", 11, "bold")).pack(anchor=W)
        tb.Entry(container, textvariable=self.url_var).pack(fill=X, pady=(4, 16))

        format_frame = tb.Labelframe(container, text="Format", padding=10)
        format_frame.pack(fill=X, pady=6)
        tb.Radiobutton(
            format_frame, text="Video (MP4)", variable=self.format_var,
            value=MediaFormat.MP4.value,
        ).pack(side=LEFT, padx=10)
        tb.Radiobutton(
            format_frame, text="Audio only (MP3)", variable=self.format_var,
            value=MediaFormat.MP3.value,
        ).pack(side=LEFT, padx=10)

        quality_frame = tb.Frame(container)
        quality_frame.pack(fill=X, pady=6)
        tb.Label(quality_frame, text="Quality:").pack(side=LEFT)
        tb.Combobox(
            quality_frame, textvariable=self.quality_var, state="readonly",
            values=[q.value for q in Quality],
        ).pack(side=LEFT, padx=8)

        trim_frame = tb.Labelframe(container, text="Trim to timestamp range", padding=10)
        trim_frame.pack(fill=X, pady=6)
        tb.Checkbutton(trim_frame, text="Enable trimming", variable=self.trim_var).pack(anchor=W)

        time_row = tb.Frame(trim_frame)
        time_row.pack(fill=X, pady=(8, 0))
        tb.Label(time_row, text="Start (HH:MM:SS)").pack(side=LEFT)
        tb.Entry(time_row, textvariable=self.start_var, width=10).pack(side=LEFT, padx=(6, 16))
        tb.Label(time_row, text="End (HH:MM:SS)").pack(side=LEFT)
        tb.Entry(time_row, textvariable=self.end_var, width=10).pack(side=LEFT, padx=6)

        output_frame = tb.Frame(container)
        output_frame.pack(fill=X, pady=6)
        tb.Label(output_frame, text="Save to:").pack(side=LEFT)
        tb.Entry(output_frame, textvariable=self.output_dir_var).pack(side=LEFT, fill=X, expand=YES, padx=6)
        tb.Button(output_frame, text="Browse", command=self._choose_output_dir).pack(side=LEFT)

        self.download_btn = tb.Button(
            container, text="Download", bootstyle=SUCCESS, command=self._on_download_clicked,
        )
        self.download_btn.pack(pady=16)

        self.progress = tb.Progressbar(container, mode="determinate", maximum=100)
        self.progress.pack(fill=X, pady=(0, 6))

        tb.Label(container, textvariable=self.status_var).pack(anchor=W)

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