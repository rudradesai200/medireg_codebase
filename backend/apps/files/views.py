from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import File, Comment
from .serializers import FileSerializer, CommentSerializer, FileWithCommentsSerialzer
from utils.permissions import ISOwner

from django.utils.translation import gettext_lazy as _
from django.http import FileResponse
from django.shortcuts import get_object_or_404

tags = [["Files"], ["Comments"]]

class FileListCreateView(APIView, PageNumberPagination):
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated]
    page_size = 5

    @extend_schema(
        summary="Get files",
        description="""
            This endpoint retreives all user's files.
        """,
        tags=tags[0],
        parameters=[
            OpenApiParameter(
                name="query",
                type=str,
                required=False,
                description="Folder name to search for",
            ),
            OpenApiParameter(
                name="page", type=int, required=False, description="Page number"
            ),
        ],
    )
    def get(self, request):
        user = request.user
        query = request.GET.get("query")
        if query == None:
            query = ""

        files = File.objects.filter(owner=user, name__icontains=query)

        if files:
            paginated_qs = self.paginate_queryset(files, request, view=self)
            serializer = self.serializer_class(
                paginated_qs, many=True, context={"request": request}
            )
            return self.get_paginated_response(
                {"data": serializer.data}, status=status.HTTP_200_OK
            )
        else:
            return Response(_("You do not have any files"))

    @extend_schema(
        summary="Upload file",
        description="""
            This endpoint uploads files.
        """,
        tags=tags[0],
    )
    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        serializer.save(owner=user)
        return Response({"data": serializer.data}, status=status.HTTP_201_CREATED)


class FileUpdateDestroyView(APIView):
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="update files",
        description="""
            This endpoint updates files.
        """,
        tags=tags,
    )
    def put(self, request, id):
        file = File.objects.get(id=id)
        serializer = self.serializer_class(
            file, data=request.data, context={"request": request}
        )
        serializer.is_valid()
        serializer.save()
        return Response({"Success": "file update succesflly", "data": serializer.data})

    @extend_schema(
        summary="Delete files",
        description="""
            This endpoint deletes files.
        """,
        tags=tags[0],
    )
    def delete(self, request, id):
        file = File.objects.get(id=id)
        if file:
            file.delete()

            return Response({"success": "file deleted succesfully"})
        else:
            return Response({"error": "File not found"})


class DownloadFileAPIView(APIView):

    @extend_schema(
        summary="Download files",
        description="""
            This endpoint returns file for download.
        """,
        tags=tags,
    )
    def get(self, request, file_id):
        try:
            file = File.objects.get(id=file_id)
        except File.DoesNotExist:
            return Response(
                {"error": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )

        file_path = file.file.path

        # Use FileResponse to handle the file download
        response = FileResponse(open(file_path, "rb"))
        response["Content-Disposition"] = f'attachment; filename="{file.file.name}"'
        return response


class CommentOnFile(APIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Comment on files",
        description="""
            This endpoint add comment to files.
        """,
        tags=tags[1],
    )
    def post(self, request, id):
        owner = request.user
        file = get_object_or_404(File, id=id)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(file=file, owner=owner)

        return Response({"data": serializer.data}, status=status.HTTP_201_CREATED)


class GetFileComments(APIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, ISOwner]

    @extend_schema(
        summary="Get comments",
        description="""
            This endpoint retreives all file's comments.
        """,
        tags=tags[1],
    )
    def get(self, request, id):
        file = File.objects.prefetch_related("comments").get(id=id)

        serializer = FileWithCommentsSerialzer(file)
        return Response({"data": serializer.data})

    @extend_schema(
        summary="Update comment",
        description="""
            This endpoint updates file's comment.
        """,
        tags=tags[1],
    )
    def put(self, request, id):
        comment = Comment.objects.get(id=id)
        serializer = self.serializer_class(comment, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"data": serializer.data})

    @extend_schema(
        summary="Delete comment",
        description="""
            This endpoint deletes a comment from file.
        """,
        tags=tags[1],
    )
    def delete(self, request, id):
        comment = Comment.objects.get(id=id)
        if request.user == comment.owner or request.user == comment.file.owner:
            comment.delete()
            return Response({"success": "comment deleted succesfully"})
        return Response(
            {"error": "you do not have the permission to delete this comment"}
        )
