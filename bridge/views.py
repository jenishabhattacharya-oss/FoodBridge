from django.shortcuts import render

def index(request):
    return render(request,'index.html')
def donate(request):
    return render(request,'donate.html')
def contact(request):
    return render(request, 'contact.html')