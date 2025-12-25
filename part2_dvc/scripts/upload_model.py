import argparse
import os
from datetime import datetime

import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--endpoint_url", default="")
    parser.add_argument("--done", required=True)
    args = parser.parse_args()

    endpoint_url = args.endpoint_url.strip() or None
    s3 = boto3.client("s3", endpoint_url=endpoint_url)

    s3.upload_file(args.model, args.bucket, args.key)

    os.makedirs(os.path.dirname(args.done), exist_ok=True)
    with open(args.done, "w", encoding="utf-8") as f:
        f.write(f"uploaded={datetime.utcnow().isoformat()}Z\n")
        f.write(f"s3://{args.bucket}/{args.key}\n")

    print(f"Uploaded to s3://{args.bucket}/{args.key}")
    print(f"Marker saved: {args.done}")


if __name__ == "__main__":
    main()
