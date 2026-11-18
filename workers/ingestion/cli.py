import argparse
from uuid import UUID

from .celery_app import poll


def main():
    parser = argparse.ArgumentParser(description="Queue a due, approved recruitment source.")
    parser.add_argument("source_id", type=UUID)
    args = parser.parse_args()
    task = poll.apply_async(args=[str(args.source_id)], expires=180)
    print(task.id)


if __name__ == "__main__":
    main()
