from app.tasks.thread import create_trending_threads_materialized_view


def main():
  create_trending_threads_materialized_view()

if __name__ == "__main__":
  main()