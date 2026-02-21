
@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Delete a channel (Super Admin only)
    
    **Params:**
    - channel_id: Channel ID
    
    **Returns:**
    - Success message
    """
    chat_service = get_redis_chat_service()
    
    # Check permissions (Super Admin only)
    roles = current_user.get('roles', [])
    # Handle both list of strings or string format if needed, but standard is list
    if not roles or 'SUPER_ADMIN' not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admins can delete channels"
        )
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    tenant_name = current_user.get('tenant_name')
    
    if not tenant_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing tenant information in token"
        )
    
    # Check if channel exists (optional, delete_channel handles it, but good for specific error)
    channel = chat_service.get_channel(channel_id)
    if not channel:
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    # Perform delete
    success = chat_service.delete_channel(tenant_name, channel_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete channel"
        )
    
    logger.info(f"Channel {channel_id} deleted by Super Admin {user_id}")
    
    return {
        "success": True,
        "message": "Channel deleted successfully"
    }
