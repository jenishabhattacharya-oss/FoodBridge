from django.shortcuts import render

def index(request):
    return render(request,'index.html')
def donate(request):
    return render(request,'donate.html')
def nearby(request):
    return render(request, 'nearby.html')