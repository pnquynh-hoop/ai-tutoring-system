from rest_framework import pagination


class ItemPaginator(pagination.PageNumberPagination):
    page_size = 10


class CommentPaginator(pagination.PageNumberPagination):
    page_size = 8
