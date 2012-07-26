""" Views """

import inspect
from annoying.decorators import render_to, ajax_request

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from djeuscan.helpers import version_key, packages_from_names, \
    get_account_categories, get_account_herds, get_account_maintainers, \
    get_account_packages
from djeuscan.models import Version, Package, Herd, Maintainer, EuscanResult, \
    VersionLog, RefreshPackageQuery, HerdAssociation, MaintainerAssociation, \
    CategoryAssociation, PackageAssociation, OverlayAssociation, ProblemReport
from djeuscan.forms import WorldForm, PackagesForm, ProblemReportForm
from djeuscan.tasks import admin_tasks
from djeuscan import charts


@render_to('euscan/index.html')
def index(request):
    context = {
        'n_packaged': Package.objects.n_packaged(),
        'n_overlay': Package.objects.n_overlay(),
        'n_versions': Package.objects.n_versions(),
        'n_upstream': Package.objects.n_upstream(),
        'n_packages': Package.objects.count(),
        'n_herds': Herd.objects.count(),
        'n_maintainers': Maintainer.objects.count(),
    }
    try:
        context['last_scan'] = EuscanResult.objects.latest().datetime
    except EuscanResult.DoesNotExist:
        context['last_scan'] = None

    return context


@render_to('euscan/logs.html')
def logs(request):
    return {}


@render_to('euscan/categories.html')
def categories(request):
    try:
        last_scan = EuscanResult.objects.latest().datetime
    except EuscanResult.DoesNotExist:
        last_scan = None

    return {'categories': Package.objects.categories(), 'last_scan': last_scan}


@render_to('euscan/category.html')
def category(request, category):
    packages = Package.objects.for_category(category, last_versions=True)

    if not packages:
        raise Http404

    try:
        last_scan = \
            EuscanResult.objects.for_category(category).latest().datetime
    except EuscanResult.DoesNotExist:
        last_scan = None

    favourited = False
    if request.user.is_authenticated():
        try:
            CategoryAssociation.objects.get(user=request.user,
                                            category=category)
        except CategoryAssociation.DoesNotExist:
            pass
        else:
            favourited = True

    return {'category': category, 'packages': packages, 'last_scan': last_scan,
            'favourited': favourited}


@render_to('euscan/herds.html')
def herds(request):
    herds = Package.objects.herds()

    try:
        last_scan = EuscanResult.objects.latest().datetime
    except EuscanResult.DoesNotExist:
        last_scan = None

    return {'herds': herds, 'last_scan': last_scan}


@render_to('euscan/herd.html')
def herd(request, herd):
    herd = get_object_or_404(Herd, herd=herd)
    packages = Package.objects.for_herd(herd, last_versions=True)

    try:
        last_scan = EuscanResult.objects.for_herd(herd).latest().datetime
    except EuscanResult.DoesNotExist:
        last_scan = None

    favourited = False
    if request.user.is_authenticated():
        try:
            HerdAssociation.objects.get(user=request.user, herd=herd)
        except HerdAssociation.DoesNotExist:
            pass
        else:
            favourited = True

    return {'herd': herd, 'packages': packages, "last_scan": last_scan,
            'favourited': favourited}


@render_to('euscan/maintainers.html')
def maintainers(request):
    maintainers = Package.objects.maintainers()

    try:
        last_scan = EuscanResult.objects.latest().datetime
    except EuscanResult.DoesNotExist:
        last_scan = None

    return {'maintainers': maintainers, 'last_scan': last_scan}


@render_to('euscan/maintainer.html')
def maintainer(request, maintainer_id):
    maintainer = get_object_or_404(Maintainer, pk=maintainer_id)
    packages = Package.objects.for_maintainer(maintainer, last_versions=True)

    try:
        last_scan = \
            EuscanResult.objects.for_maintainer(maintainer).latest().datetime
    except EuscanResult.DoesNotExist:
        last_scan = None

    favourited = False
    if request.user.is_authenticated():
        try:
            MaintainerAssociation.objects.get(user=request.user,
                                              maintainer=maintainer)
        except MaintainerAssociation.DoesNotExist:
            pass
        else:
            favourited = True

    return {'maintainer': maintainer, 'packages': packages,
            'last_scan': last_scan, 'favourited': favourited}


@render_to('euscan/overlays.html')
def overlays(request):
    overlays = Package.objects.overlays()

    try:
        last_scan = EuscanResult.objects.latest().datetime
    except EuscanResult.DoesNotExist:
        last_scan = None

    return {'overlays': overlays, 'last_scan': last_scan}


@render_to('euscan/overlay.html')
def overlay(request, overlay):
    packages = Package.objects.for_overlay(overlay)
    if not packages:
        raise Http404

    try:
        last_scan = EuscanResult.objects.latest().datetime
    except EuscanResult.DoesNotExist:
        last_scan = None

    favourited = False
    if request.user.is_authenticated():
        try:
            OverlayAssociation.objects.get(user=request.user, overlay=overlay)
        except OverlayAssociation.DoesNotExist:
            pass
        else:
            favourited = True

    return {'overlay': overlay, 'packages': packages, 'last_scan': last_scan,
            'favourited': favourited}


@render_to('euscan/package.html')
def package(request, category, package):
    package = get_object_or_404(Package, category=category, name=package)
    packaged = Version.objects.filter(package=package, packaged=True)
    upstream = Version.objects.filter(package=package, packaged=False)

    packaged = sorted(packaged, key=version_key)
    upstream = sorted(upstream, key=version_key)

    log = EuscanResult.objects.filter(package=package).\
                               order_by('-datetime')[:1]
    log = log[0] if log else None
    vlog = VersionLog.objects.for_package(package, order=True)

    try:
        last_scan = EuscanResult.objects.for_package(package).latest().datetime
    except EuscanResult.DoesNotExist:
        last_scan = None

    favourited = False
    if request.user.is_authenticated():
        try:
            PackageAssociation.objects.get(user=request.user, package=package)
        except PackageAssociation.DoesNotExist:
            pass
        else:
            favourited = True

    try:
        refreshed = request.user in \
            RefreshPackageQuery.objects.get(package=package).users.all()
    except RefreshPackageQuery.DoesNotExist:
        refreshed = False

    return {
        'package': package,
        'packaged': packaged,
        'upstream': upstream,
        'log': log.messages(),
        'vlog': vlog,
        'msg': log.messages() if log else "",
        'last_scan': last_scan,
        'favourited': favourited,
        'refreshed': refreshed,
    }


@login_required
@render_to('euscan/problem.html')
def problem(request, category, package):
    package = get_object_or_404(Package, category=category, name=package)
    packaged = Version.objects.filter(package=package, packaged=True)
    upstream = Version.objects.filter(package=package, packaged=False)

    log = EuscanResult.objects.filter(package=package).\
                               order_by('-datetime')[:1]
    log = log[0] if log else None

    thanks_for_reporting = False

    if request.method == "POST":
        form = ProblemReportForm(package, request.POST)
        if form.is_valid():
            ProblemReport(
                package=package,
                version=form.cleaned_data["version"],
                subject=form.cleaned_data["subject"],
                message=form.cleaned_data["message"],
            ).save()
            thanks_for_reporting = True
    else:
        form = ProblemReportForm(package)

    return {
        'form': form,
        'thanks_for_reporting': thanks_for_reporting,
        'package': package,
        'packaged': packaged,
        'upstream': upstream,
        'msg': log.messages() if log else "",
    }


@render_to('euscan/world.html')
def world(request):
    world_form = WorldForm()
    packages_form = PackagesForm()

    return {
        'world_form': world_form,
        'packages_form': packages_form
    }


@render_to('euscan/world_scan.html')
def world_scan(request):

    if 'world' in request.FILES:
        data = request.FILES['world'].read()
    elif 'packages' in request.POST:
        data = request.POST['packages']
    else:
        data = ""

    packages = packages_from_names(data)

    return {'packages': packages}


@render_to("euscan/about.html")
def about(request):
    return {}


@render_to("euscan/api.html")
def api(request):
    return {}


@render_to("euscan/statistics.html")
def statistics(request):
    return {}


def chart(request, **kwargs):
    from django.views.static import serve

    chart = kwargs['chart'] if 'chart' in kwargs else None

    if 'maintainer_id' in kwargs:
        kwargs['maintainer'] = get_object_or_404(
            Maintainer,
            id=kwargs['maintainer_id']
        )
    if 'herd' in kwargs:
        kwargs['herd'] = get_object_or_404(Herd, herd=kwargs['herd'])

    for kw in ('-small', '-weekly', '-monthly', '-yearly'):
        if chart.endswith(kw):
            if kw in ('-weekly', '-monthly', '-yearly'):
                kwargs['period'] = kw
            kwargs[kw] = True
            chart = chart[:-len(kw)]

    if chart == 'pie-packages':
        path = charts.pie_packages(**kwargs)
    elif chart == 'pie-versions':
        path = charts.pie_versions(**kwargs)
    elif chart == 'packages':
        path = charts.packages(**kwargs)
    elif chart == 'versions':
        path = charts.versions(**kwargs)
    else:
        raise Http404()

    return serve(request, path, document_root=charts.CHARTS_ROOT)


def chart_maintainer(request, **kwargs):
    return chart(request, **kwargs)


def chart_herd(request, **kwargs):
    return chart(request, **kwargs)


def chart_category(request, **kwargs):
    return chart(request, **kwargs)


@ajax_request
def registered_tasks(request):
    data = {}
    for task in admin_tasks:
        argspec = inspect.getargspec(task.run)
        data[task.name] = {
            "args": argspec.args,
            "defaults": argspec.defaults,
            "default_types": None
        }
        if argspec.defaults is not None:
            data[task.name].update({
                "defaults_types": [type(x).__name__ for x in argspec.defaults]
            })
    return {"tasks": data}


@login_required
@require_POST
@ajax_request
def refresh_package(request, category, package):
    pkg = get_object_or_404(Package, category=category, name=package)

    obj, created = RefreshPackageQuery.objects.get_or_create(package=pkg)

    if request.user in \
       RefreshPackageQuery.objects.get(package=pkg).users.all():
        return {"result": "failure"}

    obj.users.add(request.user)
    if not created:
        obj.priority += 1
        obj.save()
    return {"result": "success"}


@login_required
@render_to('euscan/accounts/index.html')
def accounts_index(request):
    upstream_k = lambda c: c["n_versions"] - c["n_packaged"]

    categories = sorted(get_account_categories(request.user),
                        key=upstream_k, reverse=True)
    c_upstream = sum([c["n_versions"] - c["n_packaged"] for c in categories])
    herds = sorted(get_account_herds(request.user),
                   key=upstream_k, reverse=True)
    h_upstream = sum([c["n_versions"] - c["n_packaged"] for c in herds])
    maintainers = sorted(get_account_maintainers(request.user),
                         key=upstream_k, reverse=True)
    m_upstream = sum([c["n_versions"] - c["n_packaged"] for c in maintainers])
    packages = sorted(get_account_packages(request.user),
                      key=lambda p: p.n_versions - p.n_packaged, reverse=True)
    p_upstream = sum([c.n_versions - c.n_packaged for c in packages])
    return {
        "categories": categories, "categories_upstream": c_upstream,
        "herds": herds, "herds_upstream": h_upstream,
        "maintainers": maintainers, "maintainers_upstream": m_upstream,
        "packages": packages, "packages_upstream": p_upstream,
    }


@login_required
@render_to('euscan/accounts/categories.html')
def accounts_categories(request):
    return {"categories": get_account_categories(request.user)}


@login_required
@render_to('euscan/accounts/herds.html')
def accounts_herds(request):
    return {"herds": get_account_herds(request.user)}


@login_required
@render_to('euscan/accounts/maintainers.html')
def accounts_maintainers(request):
    return {"maintainers": get_account_maintainers(request.user)}


@login_required
@render_to('euscan/accounts/packages.html')
def accounts_packages(request):
    return {"packages": get_account_packages(request.user)}


@login_required
@render_to('euscan/accounts/overlays.html')
def accounts_overlays(request):
    overlays = [obj.overlay for obj in
                OverlayAssociation.objects.filter(user=request.user)]
    return {"overlays": overlays}


@login_required
@require_POST
@ajax_request
def favourite_package(request, category, package):
    obj = get_object_or_404(Package, category=category, name=package)
    _, created = PackageAssociation.objects.get_or_create(
        user=request.user, package=obj
    )
    return {"success": created}


@login_required
@require_POST
@ajax_request
def unfavourite_package(request, category, package):
    package = get_object_or_404(Package, category=category, name=package)
    obj = get_object_or_404(
        PackageAssociation, package=package, user=request.user
    )
    obj.delete()
    return {"success": True}


@login_required
@require_POST
@ajax_request
def favourite_herd(request, herd):
    obj = get_object_or_404(Herd, herd=herd)
    _, created = HerdAssociation.objects.get_or_create(
        user=request.user, herd=obj
    )
    return {"success": created}


@login_required
@require_POST
@ajax_request
def unfavourite_herd(request, herd):
    herd = get_object_or_404(Herd, herd=herd)
    obj = get_object_or_404(
        HerdAssociation, herd=herd, user=request.user
    )
    obj.delete()
    return {"success": True}


@login_required
@require_POST
@ajax_request
def favourite_maintainer(request, maintainer_id):
    obj = get_object_or_404(Maintainer, pk=maintainer_id)
    _, created = MaintainerAssociation.objects.get_or_create(
        user=request.user, maintainer=obj
    )
    return {"success": created}


@login_required
@require_POST
@ajax_request
def unfavourite_maintainer(request, maintainer_id):
    maintainer = get_object_or_404(Maintainer, pk=maintainer_id)
    obj = get_object_or_404(
        MaintainerAssociation, maintainer=maintainer, user=request.user
    )
    obj.delete()
    return {"success": True}


@login_required
@require_POST
@ajax_request
def favourite_category(request, category):
    packages = Package.objects.for_category(category, last_versions=True)

    if not packages:
        raise Http404

    _, created = CategoryAssociation.objects.get_or_create(
        user=request.user, category=category
    )
    return {"success": created}


@login_required
@require_POST
@ajax_request
def unfavourite_category(request, category):
    obj = get_object_or_404(
        CategoryAssociation, user=request.user, category=category
    )
    obj.delete()
    return {"success": True}


@login_required
@require_POST
@ajax_request
def favourite_overlay(request, overlay):
    packages = Package.objects.for_overlay(overlay)
    if not packages:
        raise Http404

    _, created = OverlayAssociation.objects.get_or_create(
        user=request.user, overlay=overlay
    )
    return {"success": created}


@login_required
@require_POST
@ajax_request
def unfavourite_overlay(request, overlay):
    obj = get_object_or_404(
        OverlayAssociation, user=request.user, overlay=overlay
    )
    obj.delete()
    return {"success": True}
