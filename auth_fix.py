"""
FIX FOR ADMIN PERMISSIONS

The issue: embeddings_admin.py uses get_current_owner which only accepts role="owner"
But admin@admin.com has role="admin"

Add this function to auth.py:
"""

def get_current_admin_or_owner(current_restaurant: models.Restaurant = Depends(get_current_restaurant)):
    """Get the current authenticated restaurant and ensure it's an owner or admin."""
    if current_restaurant.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can perform this action"
        )
    return current_restaurant

"""
Then update embeddings_admin.py to use get_current_admin_or_owner instead of get_current_owner

OR simpler fix in auth.py line 139:

Change:
    if current_restaurant.role != "owner":

To:
    if current_restaurant.role not in ["owner", "admin"]:
"""