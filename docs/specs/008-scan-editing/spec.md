# Scan editing and reliable deletion

Users can edit an existing scan's campground, dates, minimum stay, preferred
campsite types, and electric requirement from its dashboard card or detail page.
The form starts with saved values and saves through PATCH without changing the
scan ID, creation date, or active preference. Cancel discards edits; errors keep
the form open and preserve entered values. Suspended users can edit saved scans.

Changing campground or dates links the subscription to a new or existing shared
target. Other subscribers and their results remain unchanged. Invalid date
ranges, unknown campgrounds, duplicate subscriptions, and edits to another
user's scan are rejected without changing saved data.

Card controls and delete-dialog interactions must not navigate to scan details.
Deletion requires confirmation, disables repeat submission while pending, closes
only on success, and shows failures with an opportunity to retry. Cancel leaves
the scan intact. Successful deletion refreshes the dashboard.
