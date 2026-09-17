# comment-sidecar

comment-sidecar is a **lightweight, tracking-free, self-hosted comment service**. It aims at restricted self-hosted web spaces where only **PHP and MySQL** are available. And it is easy to embed into statically generated sites that are created with Hugo or Jekyll. It's a Disqus alternative.

[![comment-sidecar frontend](docs/screenshot-frontend-400.png)](https://raw.githubusercontent.com/phauer/comment-sidecar/master/docs/screenshot-frontend.png)
 
# Features

- Tracking-free and fast. The comment-sidecar only needs two additional requests. Contrary, Disqus leads to **110 additional requests**. Read [here](http://donw.io/post/github-comments/) for more details about Disqus' tracking greed and performance impact.
- Privacy and data protection. comment-sidecar only saves the data that is required. The e-mail is optional, only used for notifications and will be deleted if the users unsubscribes from notifications. The IP is only saved for a short amount of time and can't be traced back to the e-mail. It's only used to enable rate limiting. 
- Easy to integrate. Just a simple Javascript call. This makes it easy to use the comment-sidecar in conjunction with static site generators like **Hugo** or Jekyll. You don't have to integrate PHP code in the generated HTML files.
- Lightweight: No additional PHP or JavaScript dependencies. Just drop the files on your web server and you are good to go.
- No performance impact on TTFB (Time To First Byte), because the comments are loaded asynchronously.
- Spam Protection.
- E-Mail Notification.
    - Admin receives mail for every comment.
    - Users receive Mail if there is an direct reply to their comment.
- Use one comment-sidecar installation for multiple sites.
- Replying to a comment is supported.
- Multi-language support (pull requests adding more languages are highly welcome).
- Customizable form HTML
- Import existing Disqus comments.
- Simple rate limiting based on the IP address (`$_SERVER['REMOTE_ADDR']`)

# What's Different to Disqus

- Everyone can comment. There is no registration required to write a comment.
- Currently, you can't edit or delete a post after the submission.
- There is no individual avatar. I remove the Gravatar support due to privacy concerns: I don't want to share my visitor's data with Gravatar. Moreover, it's too easy to get their E-Mail out of the MD5 hash in the image URL.

# Before and After

I migrated my [blog](https://phauer.com) from Disqus to Comment-Sidecar. Here you can see the metrics of the Chrome Dev Tools and Lighthouse. Mind, that you can achieve the same performance also with many other Disqus alternatives.

![Before and After the Disqus Migration on phauer.com](docs/before-after-phauer-com.png)

# Requirements

- PHP. Tested with 7.1.
- A MySQL database. Tested with 5.7.28.
- Some native [ECMAScript 6](http://es6-features.org/) support in the user's browser. For now, the comment-sidecar requires support for basic ECMAScript 6 features like [arrow functions](http://www.caniuse.com/#search=arrow), [`const`](http://www.caniuse.com/#search=const), [template literals](http://www.caniuse.com/#search=template) and other modern methods like [`querySelector()`](http://www.caniuse.com/#search=queryselector) and [`fetch()`](http://www.caniuse.com/#search=fetch). Currently, the supporting browser versions have a global usage of 95% - 98%. This was good enough for me. So I decided against a compilation with Babel in order to avoid a dedicated build process. However, pull requests are always welcome. Alternatively, you can compile the `comment-sidecar.js` manually once only.

# Try it out up front!

Do you want to try the comment-sidecar before you install it on your site? No problem! You only need Docker and Docker-Compose and you are ready to go.
 
```bash
docker-compose up
```

This starts a MySQL database (which already contains the required table and index), [MailHog](https://github.com/mailhog/MailHog) (a test mail server) and an Apache with PHP.

Now open [`http://localhost/playground.html`](http://localhost/playground.html) in your browser and play with the comment-sidecar in action. On [`http://localhost:8025/`](http://localhost:8025/) you can see the sent notification mails.

# Installation

Create a MySQL database and note the credentials. 

For a fresh installation, create the required tables and indexes by executing [`sql/init.sql`](sql/init.sql).

If you are upgrading an existing comment-sidecar installation that already contains comments, **do not run `sql/init.sql` again**, because that script recreates the tables. Back up the database first and run the R1.5 migrations exactly once, in this order:

```text
sql/migrations/001_add_page_id.sql
sql/migrations/002_widen_site.sql
```

The first migration adds a nullable `page_id` column and its lookup index. The second widens `site` so public site base URLs up to 255 characters can be used. Existing comments are preserved, keep `page_id = NULL`, and continue to use the historical `site + path` thread lookup until explicitly migrated.

Copy the application files from the `src` directory to your web space. Do not deploy the playground HTML files. If you are upgrading an older installation, also delete any previously deployed `phpinfo.php`; it is a diagnostic endpoint and should not be exposed on a production server. The following example assumes that the application files are put in the root directory `/`.

Open `config.php` and configure it:

```php
<?php
const LANGUAGE = "en"; # see the `translations` folder for supported languages
const SITE = "mydomain.com"; # legacy fallback if an embed does not provide data-site
const E_MAIL_FOR_NOTIFICATIONS = "your.email@domain.com"; # admin mail that will receive a notification e-mail after every new comment
const BASE_URL = "http://mydomain.com/"; # base url of the comment-sidecar backend. can differ from the embedding site.
const ALLOWED_ACCESSING_SITES = [ "http://domainA.com", "http://domainB.com" ]; # sites that are allowed to access the backend (required when the backend is deployed on a different domain than the embedding site.)

const DB_HOST = 'localhost'; # to access from host system, use 127.0.0.1
const DB_NAME = 'wb3d23s';
const DB_USER = 'wb3d23s';
const DB_PW = '1234';
const DB_PORT = 3306;

const FORM_TEMPLATE = "bootstrap-default"; # see the `form-templates` folder for the available form templates or define your own. examples: "bootstrap-default" or "bulma-default".
const BUTTON_CSS_CLASSES_ADD_COMMENT = "btn btn-link"; # css classes for the button. bootstrap: "btn btn-link". bulma: "button is-link"
const BUTTON_CSS_CLASSES_REPLY = "btn btn-link"; # css classes for the button. bootstrap: "btn btn-link". bulma: "button is-link is-small"

const RATE_LIMIT_THRESHOLD_SECONDS = "60"; # how long a user (defined by their IP) have to wait until they can comment again
const UNSUBSCRIBE_DELAY_SECONDS = "2"; # artificially delay responses of the unsubscribe link to delay brute force attacks.
```

Open the HTML file where you would like to embed the comments. The preferred embed format is:

```html
<aside id="comment-sidecar"></aside>
<script
    async
    src="https://comments.example.com/comment-sidecar-js-delivery.php"
    data-site="https://www.example.com"
    data-page-id="article-2026-001">
</script>
```

`data-site` identifies the site that owns the comment thread. When notification links are used, a public site base URL such as `https://www.example.com` is recommended because comment-sidecar combines the site value with the current page path when it builds links. The value may be up to 255 characters.

`data-page-id` is a stable identifier for the page's comment thread. It should not change when the page URL changes. For example, a page may move from `/blog/old-title/` to `/articles/new-title/` while retaining:

```html
data-page-id="article-2026-001"
```

Comments posted before and after that URL change will then belong to the same explicit thread.

The current `location.pathname` is still sent when a comment is posted. This lets comment-sidecar build links to the current page while `data-page-id` provides the stable thread identity.

For backwards compatibility:

- if `data-page-id` is omitted, comment-sidecar uses the historical `site + location.pathname` thread key;
- if `data-site` is omitted, the `SITE` value from `config.php` is used.

Existing installations can therefore adopt explicit page IDs incrementally.

`data-site` is also part of the thread identity. Existing comments keep the exact `site` value that was used when they were created. If an existing installation used a legacy value such as `mydomain.com`, either continue to use that same value in `data-site`, or migrate the stored site key before switching to a different value such as `https://www.example.com`:

```sql
UPDATE comments
SET site = 'https://www.example.com'
WHERE site = 'mydomain.com';
```

Changing `data-site` without migrating the stored rows creates a different thread namespace, so the old comments will not be found by the new site key.

### Migrating an existing path-based thread

Adding the database column does not automatically assign page IDs to existing comments. After keeping the existing site key or migrating it as described above, if a page already has comments and you want to switch that page to an explicit `data-page-id`, first back up the database and assign the same page ID to that existing thread, for example:

```sql
UPDATE comments
SET page_id = 'article-2026-001'
WHERE site = 'https://www.example.com'
  AND path = '/blog/old-title/';
```

After that, the page can move to a different URL while continuing to use `data-page-id="article-2026-001"`.

Optionally, you can include `comment-sidecar-basic.css` in the HTML header to get some basic styling. Or you can simply copy its content to your own CSS file in order to avoid a additional HTTP request.

A complete example for the frontend can be found in [`src/playground.html`](src/playground.html).

# Import Existing Disqus Comments into Comment-Sidecar

The import script needs Python 3 and the dependency management tool [Poetry](https://python-poetry.org/).

First, Export your Disqus Comments as an XML file. Details can be found [here](https://help.disqus.com/en/articles/1717164-comments-export).

Second, call

```bash
poetry shell

# print the help for the CLI
python import/import_disqus_comments.py --help 

# execute the command
python import/import_disqus_comments.py --disqus_xml_file phauer.xml --site_url https://phauer.com --cs_site_key phauer.com --db_host db_host --db_port 3306 --db_user db_user --db_password db_password --db_name db_name
``` 

# Privacy Policy

When using comment-sidecar, you might add the following to your declaration:

> Comments
>
> When entering a comment, we ask you to enter a name (doesn't have to be your real name) and your e-mail address. The e-mail is not required. We store both values along with your comment in our database and don't pass them to third-parties. Your e-mail address will never be published. If you submit an e-mail is will be used to send notifications to you when an answer to your comment is published. You can unsubscribe from these notifications and delete your e-mail address by clicking on the unsubscribe link in the e-mail.
>
> We don't use your data for ads or tracking. It's only about displaying the comment on this site and to send your notifications. That's all.
>
> You can contact us, if you want us to remove your e-mail or the whole comment from our database.
>
> Additionally, we store your IP address for a short amount of time (usually a couple of days). Your IP is not stored together with your name, e-mail or comment and can never be traced back to your personal data. We only use the IP to implement rate limiting and spam protection. After these short time, we will remove your IP from our database.

# Development

## PHP Backend Service

```bash
# start apache with php, mysql database (with the required table) and mailhog in docker containers
docker-compose up -d

# now you can execute HTTP requests like
http http://localhost/comment-sidecar.php
http POST http://localhost/comment-sidecar.php < adhoc/comment-payload.json

# develop in src/comment-sidecar.php. The changes take effect immediately. 
```

## Run the Python Tests for the Backend

Python 3.5+ and [Poetry](https://python-poetry.org/) is required. Check `python3 --version`. On Arch Linux, you can install Poetry with `yay install python-poetry`,

```bash
# start mysql database and mailhog in docker containers
docker-compose up -d

# install dependencies in a venv
poetry install 
poetry env info 
# configure your IDE with the displayed path
# now, you can execute the tests directly from the IDE

# execute all tests
poetry shell
pytest

# or only a single test:
poetry shell
pytest test/test_comment_sidecar.py
```

## Frontend

I'm using [Browsersync](https://www.browsersync.io/) to automatically reload my browser during development.

```bash
# install browsersync
npm install
# watch for changes and reload browser automatically
npm run watch
```

See [Browsersync command line usage](https://www.browsersync.io/docs/command-line) for more details.

## Test Multi-site Scenarios and Different Origins

You can use one deployed comment-sidecar backend for multiple sites. So we different domains and have to take [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS) headers into account. To simulate this locally, use the proxy server of browsersync.

```bash
# the backend runs in the php container on port 80
# let's start browsersync's proxy on port 3000
npm run watch-with-proxy
# open localhost:3000/playground.html in your browser
# it will now try to communicate with the backend on port 80
```

Alternatively, you can use IntelliJ's built-in server. Just right-click on `playground.html` and select `Open in Browser`.

## See the Sent Mails

MailHog provides a neat Web UI. Just open [`http://localhost:8025/`](http://localhost:8025/) after calling `docker-compose up`.

## Connect to the MySQL Container using a MySQL Client

Use host `127.0.0.1` instead of `localhost`! Port `3306`. Database `comment-sidecar`. User `root` and password `root`.

## Debugging with IntelliJ IDEA/PhpStorm

A tutorial for set up remote debugging of PHP code executed in a Docker container can be found [here](https://blog.philipphauer.de/debug-php-docker-container-idea-phpstorm/).
