from django.contrib import admin
from Blog.models import Post, Comments, Friendship, FriendRequest

admin.site.register(Post)
admin.site.register(Comments)
admin.site.register(Friendship)
admin.site.register(FriendRequest)
