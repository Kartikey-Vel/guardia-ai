"""
User Management Routes
Family member management and user profile endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional

from ...models.schemas import (
    User, FamilyMember, FamilyMemberCreate, APIResponse,
    PaginatedResponse
)
from ...services.user_service import UserService
from .auth import get_current_user

router = APIRouter()
user_service = UserService()

@router.get("/family", response_model=APIResponse)
async def get_family_members(current_user: User = Depends(get_current_user)):
    """Get all family members for current user"""
    try:
        family_members = await user_service.get_family_members(str(current_user.id))
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(family_members)} family members",
            data=[
                {
                    "id": str(member.id),
                    "name": member.name,
                    "relation": member.relation,
                    "phone": member.phone,
                    "email": member.email,
                    "priority_level": member.priority_level,
                    "is_active": member.is_active,
                    "created_at": member.created_at,
                    "face_encodings_count": len(member.face_encodings or []),
                    "photos_count": len(member.photos or [])
                }
                for member in family_members
            ]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve family members"
        )

@router.post("/family", response_model=APIResponse)
async def add_family_member(member_data: FamilyMemberCreate, 
                           current_user: User = Depends(get_current_user)):
    """Add a new family member"""
    try:
        member = await user_service.add_family_member(str(current_user.id), member_data)
        
        return APIResponse(
            success=True,
            message="Family member added successfully",
            data={
                "id": str(member.id),
                "name": member.name,
                "relation": member.relation
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add family member"
        )

@router.delete("/family/{member_id}", response_model=APIResponse)
async def delete_family_member(member_id: str, 
                              current_user: User = Depends(get_current_user)):
    """Delete a family member"""
    try:
        success = await user_service.delete_family_member(member_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Family member not found"
            )
        
        return APIResponse(
            success=True,
            message="Family member deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete family member"
        )
