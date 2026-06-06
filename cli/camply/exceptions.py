# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Camply: Common Exceptions
"""


class CamplyError(Exception):
    """
    Base Camply Error
    """


class SearchError(CamplyError):
    """
    Generic Search Error
    """


class CampsiteNotFoundError(SearchError):
    """
    Campsite not found Error
    """
