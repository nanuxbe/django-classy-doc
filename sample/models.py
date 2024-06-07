from django.conf import settings
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Category(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('name', )

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=9, decimal_places=2)

    class Meta:
        ordering = ('name', )

    def __str__(self):
        return self.name


class Project(models.Model):

    STATES = (
        ('draft', 'draft'),
        ('running', 'running'),
        ('finished', 'finished'),
        ('cancelled', 'cancelled'),
        ('archived', 'archived'),
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    state = models.CharField(max_length=30, choices=STATES, default='draft', editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')

    def __str__(self):
        return self.name


class Todo(models.Model):
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.description


class Feeling(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name


class Care(models.Model):
    habits = models.CharField(max_length=30)

    def __str__(self):
        return self.habits


class Enough(models.Model):
    do = models.CharField(max_length=30)

    def __str__(self):
        return self.do


class Moodtracker(models.Model):
    MOOD = (
        ("VG", "Very Good"),
        ("G", "Good"),
        ("N", "Neutral"),
        ("B", "Bad"),
        ("VB", "Very Bad"),
    )

    date = models.DateField(auto_now_add=True)
    mood_am = models.CharField(max_length=30, choices=MOOD, default='Neutral')
    mood_pm = models.CharField(max_length=30, choices=MOOD, default="Neutral")
    feelings = models.ManyToManyField(Feeling, blank=True)
    cares = models.ManyToManyField(Care, blank=True)
    stress = models.PositiveIntegerField(default=0,
                                 validators=[
                                     MaxValueValidator(5),
                                     MinValueValidator(0)
                                 ])
    energy = models.PositiveIntegerField(default=0,
                                         validators=[
                                             MaxValueValidator(10),
                                             MinValueValidator(0)
                                         ])
    what_worked = models.TextField(blank=True)
    what_didnt_work = models.TextField(blank=True)
    did_enough = models.ManyToManyField(Enough, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return str(self.date)
