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
  function renderPublications(data) {
    var el = document.getElementById("publications-list");
    if (!el) return;

    var btnStyle = "margin-right: 10px; padding: 8px 16px; font-size: 0.9rem; text-transform: uppercase;";

    var html = (data.sections || [])
      .map(function (section) {
        var heading =
          '<div class="text-left" style="margin-bottom: 10px;">' +
          '<h2 style="font-size: 1.4rem; font-weight: bold; margin-top: 20px; margin-bottom: 0;">' + section.heading + "</h2>" +
          '<hr style="border-top: 1px solid #ddd; margin-top: 5px; margin-bottom: 10px;">' +
          "</div>";

        var entries = (section.entries || [])
          .map(function (pub) {
            var divider = pub.divider_before
              ? '<hr style="border-top: 1px solid #ddd; margin: 10px 0;">'
              : "";

            var hasLinks = pub.links && pub.links.length;
            var venue = pub.venue_html
              ? '<p class="font-italic" style="margin-bottom: ' + (hasLinks ? "10px" : "0") + ';"><em>' + pub.venue_html + "</em></p>"
              : "";

            var buttons = hasLinks
              ? '<div class="d-flex flex-wrap gap-2">' +
                pub.links
                  .map(function (l) {
                    return '<a href="' + l.url + '"' + targetAttrs(l.url) +
                      ' class="btn btn-outline-dark" style="' + btnStyle + '">' + l.label + "</a>";
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
              '<h3 class="article-title" style="margin-bottom: 5px; font-size: 1.2rem;">' + pub.title + "</h3>" +
              '<p class="article-style" style="margin-bottom: 3px;">' + pub.authors_html + "</p>" +
              venue +
              buttons +
              "</div></div>"
            );
          })
          .join("\n");

        return heading + entries;
      })
      .join("\n");

    el.innerHTML = html;
  }

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", function () {
    loadYaml("/data/profile.yml").then(renderProfile).catch(function (e) { console.error(e); });
    loadYaml("/data/experience.yml").then(renderExperience).catch(function (e) { console.error(e); });
    loadYaml("/data/publications.yml").then(renderPublications).catch(function (e) { console.error(e); });
  });
})();
