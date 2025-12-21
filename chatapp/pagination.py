from rest_framework.pagination import LimitOffsetPagination, CursorPagination

# class MessageInfiniteScrollPagination(LimitOffsetPagination):
#     default_limit = 35
#     limit_query_param = 'limit'
#     offset_query_param = 'offset'

class MessageInfiniteScrollPagination(CursorPagination):
    default_limit = 10
    ordering = '-timestamp'
    cursor_query_param = 'cursor'

