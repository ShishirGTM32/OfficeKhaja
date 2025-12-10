from rest_framework.pagination import LimitOffsetPagination

class MenuInfiniteScrollPagination(LimitOffsetPagination):
    default_limit = 5
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 50
