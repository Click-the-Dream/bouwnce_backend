from app.db.postgres_db_conn import get_async_session
from app.matching_ground.model.interest import Interest
import asyncio


interests = {
    "Social & Life Style": [
        "Traveling",
        "Networking",
        "Volunteering",
        "Entrepreneurship",
        "Personal Development"
    ],
    "Entertainment": [
        "Movies",
        "Music",
        "Gaming",
        "Podcast",
        "Reading"
    ],
    
    "Fitness & Wellness": [
        "Gym/Fitness",
        "Running",
        "Yoga",
        "Sport",
        "Healthy Living"
    ],
    "Creative & Skill": [
        "Photography",
        "Writing",
        "Graphics Design",
        "Cooking",
        "Dancing"
    ],
    
    "Personality / Vibe": [
        "Deep Convesations",
        "Humor",
        "Adventurous",
        "Chill Vices",
        "Spirituality"
    ]
}

async def seed_interest():
    try:
        async with get_async_session() as session:
            await Interest.create_interests(session, interests)
        
        print("✅ Successfully seed interest")
    except Exception as e:
        print("❌ failed to seed interest", str(e))
        

def main():
    asyncio.run(seed_interest())
    
if __name__ == "__main__":
    main()
    
