from rest_framework.pagination import CursorPagination


class MessageInfiniteScrollPagination(CursorPagination):
    page_size = 15  
    ordering =  ('-timestamp', '-conversation_id') 
    cursor_query_param = 'cursor'

