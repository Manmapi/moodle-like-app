import os
import sys
import random
from pathlib import Path

# Add project root to sys.path to allow imports from app
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(project_root))

from sqlmodel import Session, select
from sqlalchemy.dialects.postgresql import insert

from app.core.db import engine as sql_engine
# Import the existing Neo4j connection instance
from app.core.neo4j import neo4j_conn 
from app.models.thread import Thread, Tag, ThreadTag
from app.data_access import neo4j as neo4j_da # Use alias to avoid name clash

MIN_TAGS_PER_THREAD = 3
MAX_TAGS_PER_THREAD = 7

def main():
    print("Starting script to randomly assign tags to threads...")

    # Verify Neo4j connection using the existing driver
    try:
        # Access the synchronous driver directly
        neo4j_conn.driver.verify_connectivity()
        print("Neo4j connection (via core.neo4j) successful.")
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        print("Script aborted.")
        return

    with Session(sql_engine) as session:
        try:
            # 1. Fetch all tags (ID and Name needed)
            print("Fetching all tags from SQL database...")
            all_tags_query = select(Tag.id, Tag.name)
            all_tags_result = session.exec(all_tags_query).all()
            if not all_tags_result:
                print("No tags found in the database. Exiting.")
                neo4j_conn.close() # Close connection if exiting early
                return
            all_tags_list = [(tag_id, tag_name) for tag_id, tag_name in all_tags_result]
            print(f"Fetched {len(all_tags_list)} tags.")

            # 2. Fetch all thread IDs
            print("Fetching all thread IDs from SQL database...")
            all_thread_ids_query = select(Thread.id)
            all_thread_ids = session.exec(all_thread_ids_query).all()
            if not all_thread_ids:
                print("No threads found in the database. Exiting.")
                neo4j_conn.close() # Close connection if exiting early
                return
            print(f"Fetched {len(all_thread_ids)} thread IDs.")

            # 3. Iterate and assign tags
            processed_threads = 0
            # Use the driver directly to create a synchronous session
            with neo4j_conn.driver.session() as neo4j_session:
                for thread_id in all_thread_ids:
                    try:
                        # 4. Determine random number of tags and select them
                        num_tags_to_add = random.randint(MIN_TAGS_PER_THREAD, MAX_TAGS_PER_THREAD)
                        sample_size = min(num_tags_to_add, len(all_tags_list))
                        if sample_size == 0:
                            continue
                            
                        selected_tags = random.sample(all_tags_list, sample_size)
                        selected_tag_ids = [tag[0] for tag in selected_tags]
                        selected_tag_names = [tag[1] for tag in selected_tags]

                        # 5. Prepare SQL Insert Data
                        sql_insert_data = [
                            {"thread_id": thread_id, "tag_id": tag_id}
                            for tag_id in selected_tag_ids
                        ]

                        # 6. Execute SQL Insert (handle conflicts)
                        sql_stmt = insert(ThreadTag).values(sql_insert_data)
                        sql_stmt = sql_stmt.on_conflict_do_nothing(
                            index_elements=['thread_id', 'tag_id'] 
                        )
                        session.execute(sql_stmt)

                        # 7. Add tags to Neo4j using the data access function
                        neo4j_da.add_tags_to_thread(
                            thread_id=thread_id,
                            tags=selected_tag_names, 
                            neo4j_session=neo4j_session # Pass the synchronous session
                        )

                        # 8. Commit SQL transaction AFTER successful Neo4j operation
                        session.commit()
                        processed_threads += 1
                        if processed_threads % 100 == 0: 
                           print(f"Processed {processed_threads}/{len(all_thread_ids)} threads...")

                    except Exception as e:
                        print(f"Error processing thread ID {thread_id}: {e}")
                        session.rollback() 
                        # continue # Uncomment if you want to continue despite errors

        except Exception as e:
            print(f"An error occurred during the main process: {e}")
            session.rollback()

    # Close Neo4j connection via the core object
    neo4j_conn.close()
    print(f"Script finished. Processed {processed_threads} threads.")

if __name__ == "__main__":
    main()
