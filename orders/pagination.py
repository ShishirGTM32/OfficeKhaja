from rest_framework.pagination import CursorPagination


class MenuInfiniteScrollPagination(CursorPagination):
    page_size = 10  
    ordering =  ('added_at') 
    cursor_query_param = 'cursor'

class MealsPagination(CursorPagination):
    page_size = 10  
    ordering = ('name')
    cursor_query_param = 'cursor'

