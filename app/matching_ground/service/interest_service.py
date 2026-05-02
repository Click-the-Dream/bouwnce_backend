# List of endpoints 
# 1. create interest
# 2. list interest
# 3. pick interest for user
# 4. list user interests
# 5. remove interest from user list of interests

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
from collections import defaultdict

from app.matching_ground.model.interest import Interest
from app.matching_ground.model.user_interest import UserInterest

from app.utils.exception import (
    BadRequestException,
    NotFoundException
)
from app.utils.helper import is_valid_uuid
from app.utils.responses import response_builder

class InterestService:
    
    async def get_all_interests(self, db: AsyncSession) -> dict[str, Any]:
        interests = await Interest.get_all(db)
        
        grouped_interests = defaultdict(list)
        
        for interest in interests:
            grouped_interests[interest.category].append(interest.name)
            
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="successfully fetched available interested grouped by category",
            data=[{"category": key, "interests": value} for key, value in grouped_interests.items()]
        )
        
    
    async def get_user_interests(self, db: AsyncSession, user_id: str) -> dict[str, Any]:
        if not is_valid_uuid(user_id):
            raise BadRequestException("Invalid user id")
        
        interests = await UserInterest.get_user_interests(db, user_id)
        interest_lists = [interest.name for interest in interests]
        
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Successfully fetched user interest",
            data={
                "interests": interest_lists
            }
        )
        
    async def add_user_interests(
        self, 
        db: AsyncSession, 
        user_id: str, 
        interest_ids: list[str]
    ) -> dict[str, Any]:
        
        if not is_valid_uuid(user_id):
            raise BadRequestException("Invalid user id")

            
        await UserInterest.add_user_interest(db, user_id, interest_ids)
        
        return response_builder(
            status_code=status.HTTP_201_CREATED,
            status="success",
            message="Successfully add user interest"
        )
        
    
    async def remove_user_interest(
        self,
        db: AsyncSession,
        user_id: str,
        interest_ids: list[str]
    ) -> dict[str, Any]:
        
        if not is_valid_uuid(user_id):
            raise BadRequestException("Invalid user id")
        
        for interest_id in interest_ids:
            if not is_valid_uuid(interest_id):
                raise BadRequestException("One of the interest ids is invalid")
            
        await UserInterest.remove_user_interests(db, user_id, interest_ids)
        
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Successfully remove user interest"
        )
        

interest_service = InterestService()