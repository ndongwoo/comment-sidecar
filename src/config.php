<?php
const LANGUAGE = "en"; # see the `translations` folder for supported languages
const SITE = "http://testdomain.com"; # legacy fallback when an embed does not set data-site. For browser writes, use an absolute public http(s) URL whose origin matches the embedding page. This value is part of thread identity; migrate existing rows before changing it.
const E_MAIL_FOR_NOTIFICATIONS = "test@localhost.de"; # admin mail that will receive a notification e-mail after every new comment
const BASE_URL = "http://localhost/"; # base url of the comment-sidecar backend. can differ from the embedding site.
const ALLOWED_ACCESSING_SITES = [ "http://localhost:1313", "http://localhost:3000", "http://testdomain.com" ]; # browser origins allowed to access the backend. A POST with Origin must also claim a site whose normalized origin matches that Origin.
const BLOCKED_IP_CIDRS = []; # optional POST denylist in CIDR notation, e.g. [ "77.238.0.0/16", "87.199.0.0/16" ]

const DB_HOST = 'mysql'; # to access from host system, use 127.0.0.1
const DB_NAME = 'comment-sidecar';
const DB_USER = 'root';
const DB_PW = 'root';
const DB_PORT = 3306;

const FORM_TEMPLATE = "bootstrap-default"; # see `form-templates` folder for the available form templates or define your own. examples: "bootstrap-default" or "bulma-default".
//const FORM_TEMPLATE = "bulma-default";
const BUTTON_CSS_CLASSES_ADD_COMMENT = "btn btn-link"; # css classes for the button. bootstrap: "btn btn-link". bulma: "button is-link"
//const BUTTON_CSS_CLASSES_ADD_COMMENT = "button is-link";
const BUTTON_CSS_CLASSES_REPLY = "btn btn-link"; # css classes for the button. bootstrap: "btn btn-link". bulma: "button is-link"
//const BUTTON_CSS_CLASSES_REPLY = "button is-link is-small";

# mind, that the following line is temporarily changed by the integration test
const RATE_LIMIT_THRESHOLD_SECONDS = "0"; # how long a user (defined by their pseudonymous IP hash) has to wait until they can comment again
const RATE_LIMIT_HASH_KEY = "test-only-change-this-to-a-long-random-secret-before-production"; # secret HMAC key used to pseudonymize rate-limit IP addresses
const UNSUBSCRIBE_DELAY_SECONDS = "0"; # artificially delay responses of the unsubscribe link to delay brute force attacks.
