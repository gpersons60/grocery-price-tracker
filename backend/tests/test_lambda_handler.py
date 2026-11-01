from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.ingestion.price_storage import StorageCounts
from backend.ingestion.import_data import ProductCounts
from backend.ingestion import lambda_handler


class FakeResponse:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = iter(chunks)

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def read(self, size: int) -> bytes:
        return next(self.chunks, b"")


def test_handler_downloads_streams_persists_and_cleans_up(
    monkeypatch, tmp_path: Path
) -> None:
    downloaded: list[tuple[str, int]] = []
    saved_paths: list[Path] = []
    product_table = object()
    observations_table = object()

    class FakeResource:
        def Table(self, name: str) -> object:
            return {"Products": product_table, "PriceObservations": observations_table}[name]

    class FakeSession:
        def __init__(self, **kwargs: Any) -> None:
            assert kwargs == {"region_name": "us-east-2"}

        def resource(self, name: str) -> FakeResource:
            assert name == "dynamodb"
            return FakeResource()

    def fake_urlopen(url: str, timeout: int) -> FakeResponse:
        downloaded.append((url, timeout))
        return FakeResponse([b"first", b"second"])

    def fake_iterator(path: Path, catalog: Any) -> iter:
        assert path.exists()
        saved_paths.append(path)
        return iter(())

    def fake_named_temporary_file(
        *, dir: str, prefix: str, suffix: str, delete: bool
    ) -> Any:
        path = tmp_path / "download.parquet"
        handle = path.open("w+b")

        class TemporaryFile:
            def __enter__(self) -> Any:
                return handle

            def __exit__(self, *args: Any) -> None:
                handle.close()

        return TemporaryFile()

    monkeypatch.setenv("PRODUCTS_TABLE", "Products")
    monkeypatch.setenv("DYNAMODB_TABLE", "PriceObservations")
    monkeypatch.setenv("AWS_REGION", "us-east-2")
    monkeypatch.setattr(lambda_handler.boto3, "Session", FakeSession)
    monkeypatch.setattr(
        lambda_handler.tempfile,
        "NamedTemporaryFile",
        fake_named_temporary_file,
    )
    monkeypatch.setattr(lambda_handler, "urlopen", fake_urlopen)
    monkeypatch.setattr(lambda_handler, "iter_normalized_observations", fake_iterator)
    monkeypatch.setattr(
        lambda_handler,
        "save_products",
        lambda table, products: ProductCounts(inserted=17),
    )
    monkeypatch.setattr(
        lambda_handler,
        "save_observations",
        lambda table, observations: StorageCounts(inserted=263),
    )

    result = lambda_handler.handler({}, None)

    assert downloaded == [(lambda_handler.SOURCE_URL, 60)]
    assert result == {
        "products": {"inserted": 17, "updated": 0, "skipped": 0},
        "priceObservations": {"inserted": 263, "updated": 0, "skipped": 0},
    }
    assert len(saved_paths) == 1
    assert not saved_paths[0].exists()


def test_handler_cleans_up_when_processing_fails(monkeypatch, tmp_path: Path) -> None:
    paths: list[Path] = []

    def fake_download(destination: Path) -> None:
        destination.write_bytes(b"source")
        paths.append(destination)

    def fake_named_temporary_file(
        *, dir: str, prefix: str, suffix: str, delete: bool
    ) -> Any:
        path = tmp_path / "download.parquet"
        handle = path.open("w+b")

        class TemporaryFile:
            def __enter__(self) -> Any:
                return handle

            def __exit__(self, *args: Any) -> None:
                handle.close()

        return TemporaryFile()

    monkeypatch.setenv("PRODUCTS_TABLE", "Products")
    monkeypatch.setenv("DYNAMODB_TABLE", "PriceObservations")
    monkeypatch.setenv("AWS_REGION", "us-east-2")
    monkeypatch.setattr(
        lambda_handler.tempfile,
        "NamedTemporaryFile",
        fake_named_temporary_file,
    )
    monkeypatch.setattr(lambda_handler, "_download_source", fake_download)
    monkeypatch.setattr(
        lambda_handler,
        "save_products",
        lambda table, products: (_ for _ in ()).throw(RuntimeError("write failed")),
    )
    monkeypatch.setattr(
        lambda_handler.boto3,
        "Session",
        lambda **kwargs: type(
            "Session",
            (),
            {"resource": lambda self, name: type(
                "Resource",
                (),
                {"Table": lambda self, table_name: object()},
            )()},
        )(),
    )

    try:
        lambda_handler.handler({}, None)
    except RuntimeError as error:
        assert str(error) == "write failed"
    else:
        raise AssertionError("processing error should propagate")

    assert len(paths) == 1
    assert not paths[0].exists()
