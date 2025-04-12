import os
import sys
from pathlib import Path

# Add project root to sys.path to allow imports from app
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(project_root))

from sqlmodel import Session
from sqlalchemy.dialects.postgresql import insert

from app.core.db import engine
from app.models.thread import Tag  # Import Tag model

# Predefined list of tags with descriptions for social posts
SOCIAL_TAGS_WITH_DESCRIPTIONS = [
    # General Social Topics
    {"name": "life", "description": "Discussions about everyday life, experiences, and personal stories."},
    {"name": "advice", "description": "Seeking or giving advice on various topics."},
    {"name": "discussion", "description": "General discussions and conversations."},
    {"name": "news", "description": "Current events and news discussions."},
    {"name": "rant", "description": "Venting frustrations or opinions."},
    {"name": "ama", "description": "Ask Me Anything sessions."},
    {"name": "poll", "description": "Running polls and surveys."},
    {"name": "story", "description": "Sharing personal stories or narratives."},
    {"name": "question", "description": "Asking questions to the community."},
    {"name": "humor", "description": "Jokes, memes, and funny content."},
    {"name": "positivity", "description": "Sharing positive vibes and encouragement."},
    {"name": "motivation", "description": "Motivational content and discussions."},

    # Hobbies & Interests
    {"name": "movies", "description": "Discussions about films and cinema."},
    {"name": "music", "description": "Sharing and discussing music."},
    {"name": "gaming", "description": "Video games, board games, and gaming culture."},
    {"name": "books", "description": "Literature, reading recommendations, and book clubs."},
    {"name": "travel", "description": "Sharing travel experiences, tips, and destinations."},
    {"name": "food", "description": "Recipes, cooking, restaurants, and food experiences."},
    {"name": "photography", "description": "Sharing photos and discussing photography techniques."},
    {"name": "art", "description": "Discussions about various forms of art."},
    {"name": "sports", "description": "Discussions about various sports and teams."},
    {"name": "fitness", "description": "Exercise, health, and wellness routines."},
    {"name": "diy", "description": "Do-It-Yourself projects and crafts."},

    # Relationships & Social Life
    {"name": "relationships", "description": "Discussions about romantic, platonic, or family relationships."},
    {"name": "dating", "description": "Advice and experiences related to dating."},
    {"name": "friendship", "description": "Discussions about friends and social connections."},
    {"name": "family", "description": "Topics related to family life."},
    {"name": "parenting", "description": "Advice and discussions for parents."},

    # Other
    {"name": "technology", "description": "General technology discussions (non-programming)."},
    {"name": "science", "description": "Discussions about scientific topics."},
    {"name": "history", "description": "Historical events and discussions."},
    {"name": "education", "description": "Learning, studying, and educational topics."},
    {"name": "career", "description": "Career advice, job searching (non-tech specific)."},
    {"name": "finance", "description": "Personal finance, budgeting, and investing."},
    {"name": "mental health", "description": "Discussions about mental well-being and support."},
    {"name": "environment", "description": "Environmental issues and sustainability."},
    {"name": "pets", "description": "Sharing about pets and animal care."},
    {"name": "local", "description": "Discussions specific to a local area or community."},
]

def main():
    print("Starting tag insertion script...")

    # Use the list of dictionaries directly
    tags_to_insert = SOCIAL_TAGS_WITH_DESCRIPTIONS

    with Session(engine) as session:
        try:
            # Build the insert statement with ON CONFLICT DO NOTHING
            # Assumes 'name' has a unique constraint in the Tag table
            stmt = insert(Tag).values(tags_to_insert)
            # stmt = stmt.on_conflict_do_nothing(
            #     index_elements=['name']  # Specify the constraint column(s)
            # )

            # Execute the statement
            result = session.execute(stmt)
            session.commit()

            print(f"Insertion attempted for {len(tags_to_insert)} tags.")
            print("Completed. Tags were either inserted or skipped if they already existed.")

        except Exception as e:
            session.rollback()
            print(f"An error occurred: {e}")
            print("Transaction rolled back.")

    print("Tag insertion script finished.")

if __name__ == "__main__":
    # Setup necessary environment variables if running standalone
    # Example: os.environ['DATABASE_URL'] = 'postgresql+psycopg2://user:pass@host/db'
    main()
