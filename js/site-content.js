/* =============================================================================
 * site-content.js
 * Renders the About, Experience, and Publications sections from the YAML data
 * files in /data/. You should NOT need to edit this file to update content —
 * edit data/profile.yml, data/experience.yml, and data/publications.yml instead.
 *
 * Requires js-yaml (loaded via CDN in index.html) to parse the .yml files.
 * ============================================================================= */

(function () {
  "use strict";

  // Fetch a YAML file and return the parsed object/array.
  function loadYaml(path) {
    return fetch(path)
      .then(function (res) {
        if (!res.ok) throw new Error("Failed to load " + path + " (" + res.status + ")");
        return res.text();
      })
      .then(function (text) {
        return jsyaml.load(text);
      });
  }

  // External links (http/https) open in a new tab; internal links (#, /) don't.
  function targetAttrs(url) {
    return /^https?:\/\//i.test(url) ? ' target="_blank" rel="noopener"' : "";
  }

  // ---------------------------------------------------------------------------
  // About / profile
  // ---------------------------------------------------------------------------
  function renderProfile(p) {
    var profileEl = document.getElementById("profile");
    if (profileEl) {
      var social = (p.social || [])
        .map(function (s) {
          return (
            '<li><a itemprop="sameAs" href="' + s.url + '"' + targetAttrs(s.url) + ">" +
            '<i class="' + s.icon + ' big-icon"></i></a></li>'
          );
        })
        .join("\n");

      profileEl.innerHTML =
        '<img class="portrait" src="' + p.avatar + '" itemprop="image" alt="Avatar">' +
        '<div class="portrait-title">' +
        '<h2 itemprop="name">' + p.name + "</h2>" +
        '<h3 itemprop="jobTitle">' + (p.title_html || "") + "</h3>" +
        '<h3 itemprop="worksFor" itemscope itemtype="http://schema.org/Organization">' +
        '<a href="' + (p.affiliation_url || "#") + '" target="_blank" itemprop="url" rel="noopener">' +
        '<span itemprop="name">' + (p.affiliation_name || "") + "</span></a></h3>" +
        "</div>" +
        '<link itemprop="url" href="">' +
        '<ul class="network-icon" aria-hidden="true">' + social + "</ul>";
    }

    var bioEl = document.getElementById("bio-content");
    if (bioEl) {
      var banner = p.banner_html
        ? '<p style="color:red;">' + p.banner_html + "</p>"
        : "";

      var paragraphs = (p.bio_html || [])
        .map(function (para) { return "<p>" + para + "</p>"; })
        .join("\n");

      var interests = (p.interests || [])
        .map(function (i) { return "<li>" + i + "</li>"; })
        .join("\n");

      var education = (p.education || [])
        .map(function (e) {
          return (
            "<li>" +
            '<i class="fa-li fas fa-graduation-cap"></i>' +
            '<div class="description">' +
            '<p class="course">' + e.course + "</p>" +
            '<p class="institution">' + e.institution + "</p>" +
            "</div></li>"
          );
        })
        .join("\n");

      bioEl.innerHTML =
        "<h1>Biography</h1>" +
        banner +
        paragraphs +
        '<div class="row">' +
        '<div class="col-md-5"><h3>Interests</h3>' +
        '<ul class="ul-interests">' + interests + "</ul></div>" +
        '<div class="col-md-7"><h3>Education</h3>' +
        '<ul class="ul-edu fa-ul">' + education + "</ul></div>" +
        "</div>";
    }
  }

  // ---------------------------------------------------------------------------
  // News / updates
  // ---------------------------------------------------------------------------
  var NEWS_STYLE =
    '<style>' +
    '.news-item{display:flex;align-items:baseline;gap:14px;padding:7px 0;' +
    'border-bottom:1px solid rgba(128,128,128,.12);}' +
    '.news-item:last-of-type{border-bottom:0;}' +
    '.news-date{flex:0 0 64px;font-weight:600;font-size:.72rem;letter-spacing:.02em;' +
    'text-transform:uppercase;color:#9aa0a6;white-space:nowrap;line-height:1.6;}' +
    '.news-text{flex:1;line-height:1.55;}' +
    '#news-toggle{margin-top:14px;padding:9px 22px;font-size:1rem;}' +
    '@media (max-width:575px){.news-item{flex-direction:column;gap:1px;}' +
    '.news-date{flex-basis:auto;}}' +
    '</style>';

  function renderNews(items) {
    var el = document.getElementById("news-list");
    if (!el) return;
    items = items || [];
    var LIMIT = 4;

    function itemHtml(n, hidden) {
      return (
        '<div class="news-item' + (hidden ? " news-extra" : "") + '"' +
        (hidden ? ' style="display:none;"' : "") + ">" +
        '<span class="news-date">' + (n.date || "") + "</span>" +
        '<span class="news-text">' + (n.html || "") + "</span>" +
        "</div>"
      );
    }

    var html = NEWS_STYLE + items
      .map(function (n, i) { return itemHtml(n, i >= LIMIT); })
      .join("\n");

    var extra = items.length - LIMIT;
    if (extra > 0) {
      html += '<button id="news-toggle" type="button" class="btn btn-outline-secondary">' +
        "Show " + extra + " more</button>";
    }
    el.innerHTML = html;

    var btn = document.getElementById("news-toggle");
    if (btn) {
      btn.addEventListener("click", function () {
        var expanded = btn.getAttribute("data-expanded") === "1";
        expanded = !expanded;
        btn.setAttribute("data-expanded", expanded ? "1" : "0");
        var extras = el.querySelectorAll(".news-extra");
        for (var i = 0; i < extras.length; i++) {
          extras[i].style.display = expanded ? "flex" : "none";
        }
        btn.textContent = expanded ? "Show less" : ("Show " + extras.length + " more");
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Service (program committees, reviewing, organizing)
  // ---------------------------------------------------------------------------
  function renderService(data) {
    var el = document.getElementById("service-list");
    if (!el) return;
    var section = document.getElementById("service");
    var nav = document.getElementById("nav-service");

    var groups = (data && Array.isArray(data.service)) ? data.service
      : (Array.isArray(data) ? data : []);
    groups = groups.filter(function (g) { return g && g.role && (g.venues || []).length; });

    if (!groups.length) {  // nothing to show -> keep section + nav hidden
      return;
    }

    // One <li> per venue: linked name + muted year.
    function venueLi(v) {
      if (typeof v === "string") return '<li class="service-venue">' + v + "</li>";
      var name = v.name || "";
      var linked = v.url ? '<a href="' + v.url + '"' + targetAttrs(v.url) + ">" + name + "</a>" : name;
      var year = v.year ? ' <span class="service-year">&middot; ' + v.year + "</span>" : "";
      return '<li class="service-venue">' + linked + year + "</li>";
    }

    var style =
      "<style>" +
      ".service-group{margin-bottom:22px;}" +
      ".service-role{font-family:Lato,sans-serif;font-size:1.05rem;font-weight:700;color:#2b2b2b;" +
      "margin:0 0 6px;padding-bottom:4px;border-bottom:1px solid rgba(128,128,128,.18);}" +
      ".service-venues{list-style:none;padding-left:0;margin:0;}" +
      ".service-venues li{padding:3px 0;line-height:1.5;}" +
      ".service-year{color:#9aa0a6;font-size:.9rem;white-space:nowrap;}" +
      "</style>";

    el.innerHTML = style + groups
      .map(function (g) {
        var venues = (g.venues || []).map(venueLi).join("\n");
        return (
          '<div class="service-group">' +
          '<div class="service-role">' + g.role + "</div>" +
          '<ul class="service-venues">' + venues + "</ul>" +
          "</div>"
        );
      })
      .join("\n");

    if (section) section.style.display = "";
    if (nav) nav.style.display = "";
  }

  // ---------------------------------------------------------------------------
  // Experience
  // ---------------------------------------------------------------------------
  function renderExperience(entries) {
    var el = document.getElementById("experience-list");
    if (!el) return;

    var last = entries.length - 1;
    el.innerHTML = entries
      .map(function (e, i) {
        var topBorder = i === 0 ? "" : "border-right";
        var botBorder = i === last ? "" : "border-right";
        var dotFill = e.current ? "exp-fill" : "";
        var location = e.location
          ? '<span class="middot-divider"></span><span>' + e.location + "</span>"
          : "";

        return (
          '<div class="row experience">' +
          '<div class="col-auto text-center flex-column d-none d-sm-flex">' +
          '<div class="row h-50"><div class="col ' + topBorder + '">&nbsp;</div><div class="col">&nbsp;</div></div>' +
          '<div class="m-2"><span class="badge badge-pill border ' + dotFill + '">&nbsp;</span></div>' +
          '<div class="row h-50"><div class="col ' + botBorder + '">&nbsp;</div><div class="col">&nbsp;</div></div>' +
          "</div>" +
          '<div class="col py-2"><div class="card"><div class="card-body">' +
          '<h4 class="card-title exp-title text-muted mt-0 mb-1">' + e.title + "</h4>" +
          '<h4 class="card-title exp-company text-muted my-0"><a href="' + e.url + '" target="_blank" rel="noopener">' + e.company + "</a></h4>" +
          '<div class="text-muted exp-meta">' + e.date + location + "</div>" +
          '<div class="card-text">' + (e.body_html || "") + "</div>" +
          "</div></div></div>" +
          "</div>"
        );
      })
      .join("\n");
  }

  // ---------------------------------------------------------------------------
  // Publications
  // ---------------------------------------------------------------------------
  var PUB_BTN_STYLE = "margin-right: 10px; padding: 8px 16px; font-size: 0.9rem; text-transform: uppercase;";

  function pubEntryHtml(pub) {
    var divider = pub.divider_before
      ? '<hr style="border-top: 1px solid #ddd; margin: 10px 0;">'
      : "";

    var hasLinks = pub.links && pub.links.length;
    var venue = pub.venue_html
      ? '<p class="font-italic" style="margin-bottom: ' + (hasLinks ? "10px" : "0") + ';"><em>' + pub.venue_html + "</em></p>"
      : "";

    // Status badges (e.g. Under Review, SRC Winner, Best Paper). Award-type tags
    // get a trophy icon in front; plain statuses (e.g. Under Review) don't.
    var tags = (pub.tags || [])
      .map(function (t) {
        var isAward = /award|winner|best\s*paper|honorable|mention|distinguished|finalist|nomin/i.test(t);
        var trophy = isAward
          ? '<i class="fas fa-trophy" title="Award" style="margin-left: 8px; margin-right: 1px; color: #e0a800; font-size: 1.05rem; vertical-align: middle;"></i>'
          : "";
        return trophy +
          '<span class="badge badge-warning" style="margin-left: ' + (isAward ? "4px" : "8px") +
          '; font-size: 0.7rem; vertical-align: middle; text-transform: uppercase;">' + t + "</span>";
      })
      .join("");

    var eqNote = pub.equal_contribution
      ? '<p class="text-muted" style="margin: 0 0 6px; font-size: 0.8rem;"><em>* Equal contribution</em></p>'
      : "";

    var buttons = hasLinks
      ? '<div class="d-flex flex-wrap gap-2">' +
        pub.links
          .map(function (l) {
            return '<a href="' + l.url + '"' + targetAttrs(l.url) +
              ' class="btn btn-outline-dark" style="' + PUB_BTN_STYLE + '">' + l.label + "</a>";
          })
          .join("") +
        "</div>"
      : "";

    return (
      divider +
      '<div class="row mb-2 d-flex align-items-center">' +
      '<div class="col-md-2 d-flex align-items-center justify-content-center" style="padding-right: 5px;">' +
      '<span class="badge badge-danger" style="font-size: 1rem; padding: 5px 10px;">' + (pub.badge || "") + "</span>" +
      "</div>" +
      '<div class="col-md-10" style="padding-left: 5px;">' +
      '<h3 class="article-title" style="margin-bottom: 5px; font-size: 1.2rem;">' + pub.title + tags + "</h3>" +
      '<p class="article-style" style="margin-bottom: 3px;">' + pub.authors_html + "</p>" +
      venue +
      eqNote +
      buttons +
      "</div></div>"
    );
  }

  function pubSectionsHtml(sections) {
    return sections
      .map(function (section) {
        var heading =
          '<div class="text-left" style="margin-bottom: 10px;">' +
          '<h2 style="font-size: 1.4rem; font-weight: bold; margin-top: 20px; margin-bottom: 0;">' + section.heading + "</h2>" +
          '<hr style="border-top: 1px solid #ddd; margin-top: 5px; margin-bottom: 10px;">' +
          "</div>";
        return heading + (section.entries || []).map(pubEntryHtml).join("\n");
      })
      .join("\n");
  }

  // selected: optional list of slugs (or {selected: [...]}) marking notable papers.
  function renderPublications(data, selected) {
    var el = document.getElementById("publications-list");
    if (!el) return;

    var allSections = data.sections || [];

    // Normalise the selected slug list.
    var slugs = Array.isArray(selected) ? selected
      : (selected && Array.isArray(selected.selected) ? selected.selected : []);
    var selectedSet = {};
    slugs.forEach(function (s) { selectedSet[s] = true; });

    // Flatten the selected papers into one curated list (document order).
    var selectedEntries = [];
    allSections.forEach(function (s) {
      (s.entries || []).forEach(function (p) {
        if (selectedSet[p.slug]) {
          var c = {}; for (var k in p) c[k] = p[k]; c.divider_before = false;
          selectedEntries.push(c);
        }
      });
    });

    // No selection configured (or none matched) -> just show everything.
    if (!selectedEntries.length) {
      el.innerHTML = pubSectionsHtml(allSections);
      return;
    }

    function pubHeading(text) {
      return '<div class="text-left" style="margin-bottom: 10px;">' +
        '<h2 style="font-size: 1.4rem; font-weight: bold; margin-top: 20px; margin-bottom: 0;">' + text + "</h2>" +
        '<hr style="border-top: 1px solid #ddd; margin-top: 5px; margin-bottom: 10px;"></div>';
    }

    var toggleAttrs =
      'type="button" class="btn btn-outline-secondary" ' +
      'style="margin-top: 16px; padding: 9px 22px; font-size: 1rem;"';

    el.innerHTML =
      '<div id="pub-selected">' +
        pubHeading("Selected Publications") +
        selectedEntries.map(pubEntryHtml).join("\n") +
      "</div>" +
      '<div id="pub-all" style="display:none;">' + pubSectionsHtml(allSections) + "</div>" +
      "<button id=\"pub-toggle\" " + toggleAttrs + ">Show all publications</button>";

    var btn = document.getElementById("pub-toggle");
    var sel = document.getElementById("pub-selected");
    var all = document.getElementById("pub-all");
    if (btn && sel && all) {
      btn.addEventListener("click", function () {
        var expanded = btn.getAttribute("data-expanded") === "1";
        expanded = !expanded;
        btn.setAttribute("data-expanded", expanded ? "1" : "0");
        sel.style.display = expanded ? "none" : "";
        all.style.display = expanded ? "" : "none";
        btn.textContent = expanded ? "Show selected only" : "Show all publications";
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", function () {
    loadYaml("/data/profile.yml").then(renderProfile).catch(function (e) { console.error(e); });
    loadYaml("/data/news.yml").then(renderNews).catch(function (e) { console.error(e); });
    loadYaml("/data/service.yml").then(renderService).catch(function (e) { console.error(e); });
    loadYaml("/data/experience.yml").then(renderExperience).catch(function (e) { console.error(e); });
    Promise.all([
      loadYaml("/data/publications.yml"),
      loadYaml("/data/selected_publications.yml").catch(function () { return null; }),
    ]).then(function (r) { renderPublications(r[0], r[1]); }).catch(function (e) { console.error(e); });
  });
})();
