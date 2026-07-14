import argparse
from datetime import datetime, timezone
from pathlib import Path

import boto3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload a trained model to S3-compatible storage"
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--endpoint_url", default="")
    parser.add_argument("--done", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_path = Path(args.model)
    if not model_path.is_file():
        raise FileNotFoundError(f"Model not found: {model_path}")
    if not args.bucket.strip() or args.bucket == "replace-with-your-bucket":
        raise ValueError("Configure a real S3 bucket before running upload")
    if not args.key.strip():
        raise ValueError("S3 object key must not be empty")

    endpoint_url = args.endpoint_url.strip() or None
    client = boto3.client("s3", endpoint_url=endpoint_url)
    client.upload_file(str(model_path), args.bucket, args.key)

    remote = client.head_object(Bucket=args.bucket, Key=args.key)
    local_size = model_path.stat().st_size
    if remote["ContentLength"] != local_size:
        raise RuntimeError(
            "Uploaded model size does not match the local artifact size"
        )

    marker_path = Path(args.done)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = Path(f"{marker_path}.tmp")
    temporary_path.write_text(
        f"uploaded={datetime.now(timezone.utc).isoformat()}\n"
        f"s3://{args.bucket}/{args.key}\n"
        f"bytes={local_size}\n",
        encoding="utf-8",
    )
    temporary_path.replace(marker_path)

    print(f"Uploaded to s3://{args.bucket}/{args.key}")
    print(f"Marker saved: {marker_path}")


if __name__ == "__main__":
    main()
