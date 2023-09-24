import hashlib
import rest_framework
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from rest_framework import viewsets, status, mixins, generics, filters
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from . import serializers
from .models import Post, Comments, Friendship, FriendRequest
from .serializers import (
    PostSerializer,
    CommentsSerializer,
    FriendshipSerializer,
    FriendRequestSerializer,
    UserSerializer,
)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        hashed_password = make_password(request.data['password'])
        request.data['password'] = hashed_password
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().order_by('-date_posted')[:100]
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            mentioned_user_info = request.data.get('mentioned_user')  # Get mentioned user info from the request data
            mentioned_user = None

            # Check if mentioned_user_info is an integer (pk) or a string (username)
            if isinstance(mentioned_user_info, int):
                try:
                    mentioned_user = User.objects.get(pk=mentioned_user_info)
                except User.DoesNotExist:
                    mentioned_user = None
            elif isinstance(mentioned_user_info, str):
                try:
                    mentioned_user = User.objects.get(username=mentioned_user_info)
                except User.DoesNotExist:
                    mentioned_user = None

            serializer.validated_data['author'] = request.user
            serializer.validated_data['mentioned_user'] = mentioned_user  # Set the mentioned_user field
            post = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class FriendshipViewSet(viewsets.ModelViewSet):
    queryset = Friendship.objects.all()
    serializer_class = FriendshipSerializer


class CommentsViewSet(viewsets.ModelViewSet):
    queryset = Comments.objects.all()
    serializer_class = CommentsSerializer

    # List comments for a specific post
    @action(detail=True, methods=['GET'])
    def list_comments_for_post(self, request, pk=None):
        post = get_object_or_404(Post, pk=pk)
        comments = Comments.objects.filter(post_id=post)
        serializer = CommentsSerializer(comments, many=True)
        return Response(serializer.data)

    # Create a comment for a specific post
    @action(detail=True, methods=['POST'])
    @login_required
    def create_comment(self, request, pk=None):
        post = get_object_or_404(Post, pk=pk)
        serializer = CommentsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.validated_data['post_id'] = post
            serializer.validated_data['user_commented'] = request.user
            comment = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Update a comment
    @action(detail=True, methods=['PUT'])
    @login_required
    def update_comment(self, request, pk=None, comment_id=None):
        post = get_object_or_404(Post, pk=pk)
        comment = get_object_or_404(Comments, pk=comment_id, post_id=post)
        if comment.user_commented != request.user:
            return Response({'error': 'You do not have permission to edit this comment.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = CommentsSerializer(comment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Delete a comment
    @action(detail=True, methods=['DELETE'])
    @login_required
    def delete_comment(self, request, pk=None, comment_id=None):
        post = get_object_or_404(Post, pk=pk)
        comment = get_object_or_404(Comments, pk=comment_id, post_id=post)
        if comment.user_commented != request.user:
            return Response({'error': 'You do not have permission to delete this comment.'}, status=status.HTTP_403_FORBIDDEN)

        comment.delete()
        return Response({'message': 'Comment deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)

class FriendRequestViewSet(viewsets.ModelViewSet):
    serializer_class = FriendRequestSerializer
    def get_queryset(self):
        user_identifier = self.kwargs.get('user_identifier')
        try:
            user_id = int(user_identifier)
            user_obj = get_object_or_404(User, id=user_id)
        except ValueError:
            user_obj = get_object_or_404(User, username=user_identifier)

        if self.action == 'received':
            return FriendRequest.objects.filter(receiver=user_obj)
        elif self.action == 'sent':
            return FriendRequest.objects.filter(sender=user_obj)
        return FriendRequest.objects.none()

    @action(detail=False, methods=['GET'], name='Received Friend Requests')
    def received(self, request, user_identifier=None):
        return self.list(request, user_identifier=user_identifier)

    @action(detail=False, methods=['GET'], name='Sent Friend Requests')
    def sent(self, request, user_identifier=None):
        return self.list(request, user_identifier=user_identifier)

class PostByUserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def get_queryset(self):
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)
        return Post.objects.filter(author=user)

class UserSearchView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email']
