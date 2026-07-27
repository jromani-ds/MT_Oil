"""Tests for the well PDF fetch batch job."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mt_oil.jobs.pdf_fetch import (
    _get_bq_api_numbers,
    _head_pdf_url,
    _download_pdf,
    _gcs_pdf_size,
    _upload_pdf,
    run,
)


class FakeResponse:
    def __init__(self, data: bytes, headers: dict | None = None):
        self._data = data
        self._pos = 0
        self.headers = headers or {}
        self.status = 200

    def read(self, n: int = -1):
        if n == -1 or n is None:
            result = self._data[self._pos :]
            self._pos = len(self._data)
        else:
            result = self._data[self._pos : self._pos + n]
            self._pos += n
        return result

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeBlob:
    def __init__(self, name: str, exists: bool = False, size: int | None = None):
        self.name = name
        self._exists = exists
        self.size = size or 0

    def exists(self):
        return self._exists

    def reload(self):
        pass

    def upload_from_filename(self, path: str | Path):
        pass


class FakeBucket:
    def __init__(self):
        self.blobs: dict[str, FakeBlob] = {}

    def blob(self, name: str) -> FakeBlob:
        if name not in self.blobs:
            self.blobs[name] = FakeBlob(name)
        return self.blobs[name]


class FakeClient:
    def __init__(self):
        self.bucket = FakeBucket()

    def bucket(self, name: str) -> FakeBucket:
        return self.bucket


class FakeQueryJob:
    def __init__(self, rows: list):
        self._rows = rows

    def result(self):
        return self

    def __iter__(self):
        return iter(self._rows)


class FakeRow:
    def __init__(self, api_wellno: str):
        self.api_wellno = api_wellno


@pytest.fixture(autouse=True)
def mock_settings():
    with patch("mt_oil.jobs.pdf_fetch.settings") as mock:
        mock.gcp_project_id = "test-project"
        mock.bigquery_dataset = "test_dataset"
        mock.gcs_data_bucket = "test-bucket"
        yield mock


@pytest.fixture
def mock_bq():
    rows = [FakeRow(f"250000000{i:04d}") for i in range(5)]
    with patch("mt_oil.jobs.pdf_fetch.bigquery.Client") as mock_cls:
        instance = MagicMock()
        instance.query.return_value = FakeQueryJob(rows)
        mock_cls.return_value = instance
        yield mock_cls


def test_get_bq_api_numbers(mock_bq):
    result = _get_bq_api_numbers()
    assert len(result) == 5
    assert result[0] == "2500000000000"
    assert result[-1] == "2500000000004"


@patch("mt_oil.jobs.pdf_fetch.urlopen")
def test_head_pdf_url_success(mock_urlopen):
    headers = {"Content-Length": "12345", "Content-Type": "application/pdf"}
    mock_urlopen.return_value.__enter__.return_value.headers = headers
    mock_urlopen.return_value.__enter__.return_value.status = 200

    size, ctype = _head_pdf_url("2500000000000")
    assert size == 12345
    assert ctype == "application/pdf"


@patch("mt_oil.jobs.pdf_fetch.urlopen")
def test_head_pdf_url_no_content_length(mock_urlopen):
    headers = {"Content-Type": "application/pdf"}
    mock_urlopen.return_value.__enter__.return_value.headers = headers

    size, ctype = _head_pdf_url("2500000000000")
    assert size is None
    assert ctype == "application/pdf"


@patch("mt_oil.jobs.pdf_fetch.urlopen")
def test_head_pdf_url_http_error(mock_urlopen):
    from urllib.error import HTTPError

    mock_urlopen.side_effect = HTTPError(
        "http://example.com", 404, "Not Found", {}, None
    )
    size, ctype = _head_pdf_url("2500000000000")
    assert size is None
    assert ctype is None


@patch("mt_oil.jobs.pdf_fetch.urlopen")
def test_download_pdf_success(mock_urlopen, tmp_path):
    pdf_data = b"%PDF-1.4 fake pdf content"
    headers = {"Content-Type": "application/pdf"}
    fake_resp = FakeResponse(pdf_data, headers)
    mock_urlopen.return_value = fake_resp

    dest = tmp_path / "test.pdf"
    result = _download_pdf("2500000000000", dest)
    assert result is True
    assert dest.read_bytes() == pdf_data


@patch("mt_oil.jobs.pdf_fetch.urlopen")
def test_download_pdf_wrong_content_type(mock_urlopen, tmp_path):
    html_data = b"<html>not a pdf</html>"
    headers = {"Content-Type": "text/html"}
    fake_resp = FakeResponse(html_data, headers)
    mock_urlopen.return_value = fake_resp

    dest = tmp_path / "test.pdf"
    result = _download_pdf("2500000000000", dest)
    assert result is False
    assert not dest.exists()


@patch("mt_oil.jobs.pdf_fetch.urlopen")
def test_download_pdf_empty_body(mock_urlopen, tmp_path):
    headers = {"Content-Type": "application/pdf"}
    fake_resp = FakeResponse(b"", headers)
    mock_urlopen.return_value = fake_resp

    dest = tmp_path / "test.pdf"
    result = _download_pdf("2500000000000", dest)
    assert result is False
    assert not dest.exists()


@patch("mt_oil.jobs.pdf_fetch.storage.Client")
def test_gcs_pdf_size_exists(mock_storage_cls):
    instance = MagicMock()
    bucket = FakeBucket()
    bucket.blobs["wells/pdfs/2500000000000.pdf"] = FakeBlob(
        "wells/pdfs/2500000000000.pdf", exists=True, size=54321
    )
    instance.bucket.return_value = bucket
    mock_storage_cls.return_value = instance

    size = _gcs_pdf_size("2500000000000")
    assert size == 54321


@patch("mt_oil.jobs.pdf_fetch.storage.Client")
def test_gcs_pdf_size_not_exists(mock_storage_cls):
    instance = MagicMock()
    bucket = FakeBucket()
    instance.bucket.return_value = bucket
    mock_storage_cls.return_value = instance

    size = _gcs_pdf_size("2500000000000")
    assert size is None


@patch("mt_oil.jobs.pdf_fetch.storage.Client")
def test_upload_pdf(mock_storage_cls, tmp_path):
    instance = MagicMock()
    bucket = FakeBucket()
    instance.bucket.return_value = bucket
    mock_storage_cls.return_value = instance

    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake content")

    _upload_pdf("2500000000000", pdf)


@patch("mt_oil.jobs.pdf_fetch.storage.Client")
@patch("mt_oil.jobs.pdf_fetch.urlopen")
@patch("mt_oil.jobs.pdf_fetch._get_bq_api_numbers")
def test_run_skips_when_same_size(
    mock_bq, mock_urlopen, mock_storage_cls, mock_settings
):
    mock_bq.return_value = ["2500000000000", "2500000000001"]

    headers = {"Content-Length": "100", "Content-Type": "application/pdf"}

    def urlopen_side_effect(req, **kwargs):
        resp = MagicMock()
        resp.headers = headers
        resp.status = 200
        resp.__enter__.return_value = resp
        return resp

    mock_urlopen.side_effect = urlopen_side_effect

    instance = MagicMock()
    blob = FakeBlob("wells/pdfs/2500000000000.pdf", exists=True, size=100)
    blob2 = FakeBlob("wells/pdfs/2500000000001.pdf", exists=True, size=100)

    def blob_side_effect(name):
        if "2500000000000" in name:
            return blob
        return blob2

    bucket = MagicMock()
    bucket.blob.side_effect = blob_side_effect
    instance.bucket.return_value = bucket
    mock_storage_cls.return_value = instance

    result = run(delay=0.01, max_wells=2)
    assert result is None


@patch("mt_oil.jobs.pdf_fetch.storage.Client")
@patch("mt_oil.jobs.pdf_fetch.urlopen")
@patch("mt_oil.jobs.pdf_fetch._get_bq_api_numbers")
def test_run_fetches_when_size_differs(
    mock_bq, mock_urlopen, mock_storage_cls, mock_settings, tmp_path
):
    mock_bq.return_value = ["2500000000000"]

    def urlopen_side_effect(req, **kwargs):
        if req.method == "HEAD":
            resp = MagicMock()
            resp.headers = {"Content-Length": "200", "Content-Type": "application/pdf"}
            resp.status = 200
            resp.__enter__.return_value = resp
            return resp
        pdf_data = b"%PDF-1.4 updated content"
        fake_resp = FakeResponse(pdf_data, {"Content-Type": "application/pdf"})
        return fake_resp

    mock_urlopen.side_effect = urlopen_side_effect

    instance = MagicMock()
    blob = FakeBlob("wells/pdfs/2500000000000.pdf", exists=True, size=100)
    bucket = MagicMock()
    bucket.blob.return_value = blob
    instance.bucket.return_value = bucket
    mock_storage_cls.return_value = instance

    with patch("mt_oil.jobs.pdf_fetch.tempfile.NamedTemporaryFile") as mock_tmp:
        mock_tmp.return_value.__enter__.return_value.name = str(tmp_path / "tmp.pdf")
        result = run(delay=0.01, max_wells=1)
    assert result is None


@patch("mt_oil.jobs.pdf_fetch.storage.Client")
@patch("mt_oil.jobs.pdf_fetch.urlopen")
@patch("mt_oil.jobs.pdf_fetch._get_bq_api_numbers")
def test_run_handles_non_pdf_content_type(
    mock_bq, mock_urlopen, mock_storage_cls, mock_settings
):
    mock_bq.return_value = ["2500000000000"]

    headers = {"Content-Length": "500", "Content-Type": "text/html"}
    resp = MagicMock()
    resp.headers = headers
    resp.status = 200
    resp.__enter__.return_value = resp
    mock_urlopen.return_value = resp

    instance = MagicMock()
    blob = FakeBlob("wells/pdfs/2500000000000.pdf", exists=False)
    bucket = MagicMock()
    bucket.blob.return_value = blob
    instance.bucket.return_value = bucket
    mock_storage_cls.return_value = instance

    result = run(delay=0.01, max_wells=1)
    assert result is None


@patch("mt_oil.jobs.pdf_fetch.storage.Client")
@patch("mt_oil.jobs.pdf_fetch.urlopen")
@patch("mt_oil.jobs.pdf_fetch._get_bq_api_numbers")
def test_run_with_no_bucket_raises(
    mock_bq, mock_urlopen, mock_storage_cls, mock_settings
):
    mock_settings.gcs_data_bucket = ""
    mock_bq.return_value = ["2500000000000"]

    with pytest.raises(EnvironmentError, match="GCS_DATA_BUCKET"):
        run(delay=0.01, max_wells=1)
