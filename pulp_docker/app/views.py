from rest_framework import response, views


class VersionView(views.APIView):
    """
    APIView for Docker Registry v2 root.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """
        Return a response to the "GET" action.
        """
        return response.Response({})
