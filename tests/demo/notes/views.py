from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .forms import NoteForm


@login_required
def note_list(request: HttpRequest) -> HttpResponse:
    # Plain ORM: TenantRouter sends this query to the current tenant's database.
    form = NoteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        note = form.save(commit=False)
        note.author = request.user
        note.save()
        return redirect("notes:list")
    notes = request.user.notes.all()  # ty: ignore[unresolved-attribute]
    return render(request, "notes/note_list.html", {"notes": notes, "form": form})
