from rest_framework.pagination import CursorPagination


class MenuInfiniteScrollPagination(CursorPagination):
    page_size = 10  
    ordering =  ('created_at') 
    cursor_query_param = 'cursor'

class MealsPagination(CursorPagination):
    page_size = 15 
    ordering = ('name')
    cursor_query_param = 'cursor'
