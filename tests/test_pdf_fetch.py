"""Tests for the well PDF fetch batch job."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mt_oil.jobs.pdf_fetch import (
    _get_bq_api_numbers,
    _pdf_url,
    _gcs_blob_name,
    _head_pdf,
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


class TestPdfUrl:
    def test_full_14_digit(self):
        assert _pdf_url("25091212570000") == (
            "https://bogfiles.dnrc.mt.gov/Well_Data/2509121257/2509121257.pdf"
        )

    def test_pads_to_14(self):
        assert _pdf_url("2509121257") == (
            "https://bogfiles.dnrc.mt.gov/Well_Data/2509121257/2509121257.pdf"
        )

    def test_does_not_include_event_code(self):
        url = _pdf_url("25091212570000")
        assert "2509121257" in url
        assert "25091212570000" not in url

    def test_returns_none_for_short_string(self):
        assert _pdf_url("123") is None


class TestGcsBlobName:
    def test_uses_first_10_digits_in_filename(self):
        assert _gcs_blob_name("25091212570000") == (
            "wells/pdfs/25091212570000/2509121257.pdf"
        )

    def test_pads_short_api(self):
        assert _gcs_blob_name("2509121257") == ("wells/pdfs/2509121257/2509121257.pdf")


class TestHeadPdf:
    def test_well_with_pdf(self):
        with patch("mt_oil.jobs.pdf_fetch.urlopen") as mock_urlopen:
            headers = {"Content-Length": "48539067", "Content-Type": "application/pdf"}
            mock_urlopen.return_value.__enter__.return_value.headers = headers
            mock_urlopen.return_value.__enter__.return_value.status = 200

            url, size = _head_pdf("25091212570000")
            assert url == (
                "https://bogfiles.dnrc.mt.gov/Well_Data/2509121257/2509121257.pdf"
            )
            assert size == 48539067

    def test_well_without_pdf(self):
        from urllib.error import HTTPError

        with patch("mt_oil.jobs.pdf_fetch.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                "http://example.com", 404, "Not Found", {}, None
            )
            url, size = _head_pdf("25091212570000")
            assert url is None
            assert size is None

    def test_network_error(self):
        from urllib.error import URLError

        with patch("mt_oil.jobs.pdf_fetch.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = URLError("timeout")
            url, size = _head_pdf("25091212570000")
            assert url is None
            assert size is None

    def test_invalid_api_number(self):
        url, size = _head_pdf("123")
        assert url is None
        assert size is None

    def test_no_content_length_header(self):
        with patch("mt_oil.jobs.pdf_fetch.urlopen") as mock_urlopen:
            headers = {"Content-Type": "application/pdf"}
            mock_urlopen.return_value.__enter__.return_value.headers = headers

            url, size = _head_pdf("25091212570000")
            assert url is not None
            assert size is None


class TestDownloadPdf:
    def test_success(self, tmp_path):
        pdf_data = b"%PDF-1.4 fake pdf content"
        with patch("mt_oil.jobs.pdf_fetch.urlopen") as mock_urlopen:
            fake_resp = FakeResponse(pdf_data, {"Content-Type": "application/pdf"})
            mock_urlopen.return_value = fake_resp

            dest = tmp_path / "test.pdf"
            pdf_url = "https://bogfiles.dnrc.mt.gov/Well_Data/2509121257/2509121257.pdf"
            result = _download_pdf(pdf_url, dest)
            assert result is True
            assert dest.read_bytes() == pdf_data

    def test_wrong_content_type(self, tmp_path):
        with patch("mt_oil.jobs.pdf_fetch.urlopen") as mock_urlopen:
            html_data = b"<html>not a pdf</html>"
            fake_resp = FakeResponse(html_data, {"Content-Type": "text/html"})
            mock_urlopen.return_value = fake_resp

            dest = tmp_path / "test.pdf"
            pdf_url = "https://bogfiles.dnrc.mt.gov/Well_Data/2509121257/2509121257.pdf"
            result = _download_pdf(pdf_url, dest)
            assert result is False
            assert not dest.exists()

    def test_empty_body(self, tmp_path):
        with patch("mt_oil.jobs.pdf_fetch.urlopen") as mock_urlopen:
            fake_resp = FakeResponse(b"", {"Content-Type": "application/pdf"})
            mock_urlopen.return_value = fake_resp

            dest = tmp_path / "test.pdf"
            pdf_url = "https://bogfiles.dnrc.mt.gov/Well_Data/2509121257/2509121257.pdf"
            result = _download_pdf(pdf_url, dest)
            assert result is False
            assert not dest.exists()

    def test_network_error(self, tmp_path):
        from urllib.error import URLError

        with patch("mt_oil.jobs.pdf_fetch.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = URLError("timeout")

            dest = tmp_path / "test.pdf"
            pdf_url = "https://bogfiles.dnrc.mt.gov/Well_Data/2509121257/2509121257.pdf"
            result = _download_pdf(pdf_url, dest)
            assert result is False


class TestGcsOperations:
    def test_size_exists(self):
        with patch("mt_oil.jobs.pdf_fetch.storage.Client") as mock_cls:
            instance = MagicMock()
            blob = FakeBlob(
                "wells/pdfs/25091212570000/2509121257.pdf", exists=True, size=54321
            )

            def blob_side(name):
                return blob

            instance.bucket.return_value.blob = blob_side
            mock_cls.return_value = instance

            size = _gcs_pdf_size("25091212570000")
            assert size == 54321

    def test_size_not_exists(self):
        with patch("mt_oil.jobs.pdf_fetch.storage.Client") as mock_cls:
            instance = MagicMock()
            blob = FakeBlob("wells/pdfs/25091212570000/2509121257.pdf", exists=False)

            def blob_side(name):
                return blob

            instance.bucket.return_value.blob = blob_side
            mock_cls.return_value = instance

            size = _gcs_pdf_size("25091212570000")
            assert size is None

    def test_upload(self, tmp_path):
        with patch("mt_oil.jobs.pdf_fetch.storage.Client") as mock_cls:
            instance = MagicMock()
            blob = FakeBlob("wells/pdfs/25091212570000/2509121257.pdf")
            instance.bucket.return_value.blob.return_value = blob
            mock_cls.return_value = instance

            pdf = tmp_path / "test.pdf"
            pdf.write_bytes(b"%PDF fake content")
            _upload_pdf("25091212570000", pdf)


class TestRun:
    def test_no_bucket_raises(self, mock_settings):
        mock_settings.gcs_data_bucket = ""
        with pytest.raises(EnvironmentError, match="GCS_DATA_BUCKET"):
            run(delay=0.01, max_wells=1)

    def test_skips_when_same_size(self):
        with (
            patch("mt_oil.jobs.pdf_fetch._get_bq_api_numbers") as mock_bq,
            patch("mt_oil.jobs.pdf_fetch.urlopen") as mock_urlopen,
            patch("mt_oil.jobs.pdf_fetch.storage.Client") as mock_storage,
        ):
            mock_bq.return_value = ["25091212570000"]

            urlopen_side = MagicMock()
            urlopen_side.__enter__.return_value.headers = {
                "Content-Length": "48539067",
                "Content-Type": "application/pdf",
            }
            urlopen_side.__enter__.return_value.status = 200
            mock_urlopen.return_value = urlopen_side

            storage_instance = MagicMock()
            blob = FakeBlob(
                "wells/pdfs/25091212570000/2509121257.pdf",
                exists=True,
                size=48539067,
            )
            storage_instance.bucket.return_value.blob.return_value = blob
            mock_storage.return_value = storage_instance

            result = run(delay=0.01, max_wells=1)
            assert result is None

    def test_fetches_when_size_differs(self, tmp_path):
        with (
            patch("mt_oil.jobs.pdf_fetch._get_bq_api_numbers") as mock_bq,
            patch("mt_oil.jobs.pdf_fetch.urlopen") as mock_urlopen,
            patch("mt_oil.jobs.pdf_fetch.storage.Client") as mock_storage,
            patch("mt_oil.jobs.pdf_fetch.tempfile.NamedTemporaryFile") as mock_tmp,
        ):
            mock_bq.return_value = ["25091212570000"]

            mock_tmp.return_value.__enter__.return_value.name = str(
                tmp_path / "tmp.pdf"
            )

            head_headers = {
                "Content-Length": "50000000",
                "Content-Type": "application/pdf",
            }

            def urlopen_side_effect(req, **kwargs):
                if req.method == "HEAD":
                    resp = MagicMock()
                    resp.headers = head_headers
                    resp.status = 200
                    resp.__enter__.return_value = resp
                    return resp
                fake_resp = FakeResponse(
                    b"%PDF-1.4 updated content",
                    {"Content-Type": "application/pdf"},
                )
                return fake_resp

            mock_urlopen.side_effect = urlopen_side_effect

            storage_instance = MagicMock()
            blob = FakeBlob(
                "wells/pdfs/25091212570000/2509121257.pdf",
                exists=True,
                size=48539067,
            )
            storage_instance.bucket.return_value.blob.return_value = blob
            mock_storage.return_value = storage_instance

            result = run(delay=0.01, max_wells=1)
            assert result is None

    def test_no_pdf_on_server(self):
        from urllib.error import HTTPError

        with (
            patch("mt_oil.jobs.pdf_fetch._get_bq_api_numbers") as mock_bq,
            patch("mt_oil.jobs.pdf_fetch.urlopen") as mock_urlopen,
            patch("mt_oil.jobs.pdf_fetch.storage.Client") as mock_storage,
        ):
            mock_bq.return_value = ["25047208580000"]

            mock_urlopen.side_effect = HTTPError(
                "http://example.com", 404, "Not Found", {}, None
            )

            storage_instance = MagicMock()
            blob = FakeBlob(
                "wells/pdfs/25047208580000/2504720858.pdf",
                exists=False,
            )
            storage_instance.bucket.return_value.blob.return_value = blob
            mock_storage.return_value = storage_instance

            result = run(delay=0.01, max_wells=1)
            assert result is None
