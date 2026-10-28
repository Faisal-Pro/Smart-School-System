"""Give every course the right picture, matching by words in the course name.

Run:  python manage.py set_course_images          (shows what it would do)
      python manage.py set_course_images --apply  (saves it)
"""
from django.core.management.base import BaseCommand

from School.models import Courses

# (words that must appear in the lower-case course name, image file)
RULES = [
    (("discrete",), "course_discrete_math.jpg"),
    (("introduction", "computer"), "course_intro_cs.jpg"),
    (("intro", "computer"), "course_intro_cs.jpg"),
    (("object",), "course_oop.jpg"),
    (("oop",), "course_oop.jpg"),
    (("data structure",), "course_data_structures.jpg"),
    (("algorithm",), "course_data_structures.jpg"),
    (("architecture",), "course_computer_architecture.jpg"),
    (("operating",), "course_operating_systems.jpg"),
    (("database",), "course_databases.jpg"),
    (("network",), "course_computer_networks.jpg"),
    (("software",), "course_software_engineering.jpg"),
    (("security",), "course_information_security.jpg"),
    (("artificial",), "course_ai_ml.jpg"),
    (("machine",), "course_ai_ml.jpg"),
    (("graduation",), "course_graduation_project.jpg"),
    (("project",), "course_graduation_project.jpg"),
    (("physics",), "Physics.jpg"),
    (("math",), "Math.jpg"),
]


def pick(name):
    low = name.lower()
    for words, image in RULES:
        if all(w in low for w in words):
            return image
    return "default-course.jpg"


class Command(BaseCommand):
    help = "Set image_url of every course from its name."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **opts):
        for c in Courses.objects.all().order_by("course_id"):
            image = pick(c.course_name)
            self.stdout.write(f"{c.course_id:>4}  {c.course_name:<38} -> {image}")
            if opts["apply"]:
                c.image_url = image
                c.save(update_fields=["image_url"])
        if not opts["apply"]:
            self.stdout.write("\nNothing saved. Add --apply to save.")
