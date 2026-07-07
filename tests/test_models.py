from getclip.core.models import DownloadJob


def test_job_is_not_trimmed_by_default():
    job = DownloadJob(url="https://example.com", output_dir="/tmp")
    assert job.is_trimmed is False


def test_job_is_trimmed_when_both_times_set():
    job = DownloadJob(url="https://example.com", output_dir="/tmp", start_seconds=10, end_seconds=20)
    assert job.is_trimmed is True


def test_job_is_not_trimmed_with_only_start():
    job = DownloadJob(url="https://example.com", output_dir="/tmp", start_seconds=10)
    assert job.is_trimmed is False