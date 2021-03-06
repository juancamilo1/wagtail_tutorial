import datetime

from datetime import date

from django import forms
from django.db import models
from django.http import Http404, HttpResponse
from django.utils.dateformat import DateFormat
from django.utils.formats import date_format

from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.tags import ClusterTaggableManager

from taggit.models import TaggedItemBase, Tag as TaggitTag

from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.core.models import Page
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.core.fields import RichTextField
from wagtail.snippets.models import register_snippet

class BlogPage(RoutablePageMixin, Page):
    description = models.CharField(max_length=255, blank=True,)

    content_panels = Page.content_panels + [
        FieldPanel("description", classname = "full")
    ]

    def get_context(self, request, *args, **kargs):
        context = super(BlogPage, self).get_context(request, *args, **kargs)
        context['posts'] = self.posts
        context['blog_page'] = self
        return context
    
    def get_posts(self):
        return PostPage.objects.descendant_of(self).live().order_by("-date")

    @route(r'^(d{4})/$')
    @route(r'^(\d{4})/(\d{2})/$')
    @route(r'^(\d{4})/(\d{2})/(\d{2})/$')
    def post_by_date(self, request, year, month=None, day=None, *args, **kargs):
        self.posts = self.get_posts().filter(date__year=year)
        if month:
            self.posts = self.posts.filter(date__month=month)
            df = DateFormat(date(int(year), int(month), 1))
            self.search_term = df.format("F Y")
        if day:
            self.posts = self.posts.filter(date__day=day)
            self.search_term = date_format(date(int(year), int(month), int(day)))        
        return Page.serve(self, request, *args, **kargs) 

    @route(r'^(\d{4})/(\d{2})/(\d{2})/(.+)/$')
    def post_by_date_slug(self, request, year, month, day, slug, *args, **kargs):
        post_page = self.get_posts().filter(slug=slug).first()
        if not post_page:
            raise Http404
        return Page.serve(post_page, request, *args, **kargs)

    @route(r'^tag/(?P<tag>[-\w]+)/$') 
    def post_by_tag(self, request, tag, *args, **kargs):
        self.search_type = "tag"
        self.search_term = tag
        self.posts = self.get_posts().filter(tags__slug=tag)
        return Page.serve(self, request, *args, **kargs)
 
    @route(r'^category/(?P<category>[-\w]+)/$')
    def post_by_category(self, request, category, *args, **kargs):
        self.search_type = "category"
        self.search_term = category
        self.posts = self.get_posts().filter(categories__slug=category)
        return Page.serve(self, request, *args, **kargs)

    @route(r'^$')
    def post_list(self, request, *args, **kargs):
        self.posts = self.get_posts()
        return Page.serve(self, request, *args, **kargs)
class PostPage(Page):
    body = RichTextField(blank=True)
    date = models.DateTimeField(verbose_name="Post date", default=datetime.datetime.today)
    categories = ParentalManyToManyField("blog.BlogCategory", blank=True)
    tags = ClusterTaggableManager(through="blog.BlogPageTag", blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("body", classname = "full"),
        FieldPanel("categories", widget=forms.CheckboxSelectMultiple),
        FieldPanel("tags"),
    ]

    settings_panels = Page.settings_panels + [
        FieldPanel("date"),
    ]

    @property
    def blog_page(self):
        return self.get_parent().specific

    def get_context(self, request, *args, **kargs):
        context = super(PostPage, self).get_context(request, *args, **kargs)
        context['blog_page'] = self.blog_page
        context['post'] = self
        return context

class BlogPageTag(TaggedItemBase):
    content_object = ParentalKey('PostPage', related_name = "post_tags")

@register_snippet
class Tag(TaggitTag):
    class Meta:
        proxy = True

@register_snippet
class BlogCategory(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=80)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug")
    ]

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

