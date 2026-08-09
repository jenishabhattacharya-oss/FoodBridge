from django.shortcuts import redirect, render

def index(request):
    return render(request,'index.html')
def donate(request):
    return redirect("donation_create")
def contact(request):
    return render(request, 'contact.html')
