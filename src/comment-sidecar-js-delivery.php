<?php
include_once __DIR__ . "/common.php";

function deliverJsWithTranslationsAndPath(){
    header('Content-Type: application/javascript; charset=UTF-8');
    $language = resolveTranslationLanguage($_GET['lang'] ?? null);
    header("Content-Language: $language");

    $jsTemplate = __DIR__ . '/comment-sidecar.js';
    if (!file_exists($jsTemplate)) {
        throw new RuntimeException("JavaScript template is unavailable.");
    }

    $page = file_get_contents($jsTemplate);
    if ($page === false) {
        throw new RuntimeException("JavaScript template could not be read.");
    }

    // poor man's templating (but at least I prevent nice tooling in the js and html file)
    $page = str_replace("{{FORM_HTML}}", readFormTemplate(), $page);
    $page = str_replace("{{BUTTON_CSS_CLASSES_ADD_COMMENT}}", BUTTON_CSS_CLASSES_ADD_COMMENT, $page);
    $page = str_replace("{{BUTTON_CSS_CLASSES_REPLY}}", BUTTON_CSS_CLASSES_REPLY, $page);
    foreach (readTranslations($language) as $key => $translation) {
        $page = str_replace("{{".$key."}}",$translation,$page);
    }
    $page = str_replace("{{LANGUAGE}}", $language, $page);
    $page = str_replace("{{SITE}}",SITE,$page);
    $currentDir = BASE_URL;
    $page = str_replace("{{BASE_PATH}}","{$currentDir}comment-sidecar.php", $page);
    echo $page;
}

function readFormTemplate(): string {
    $formTemplateFile = __DIR__ . '/form-templates/'. FORM_TEMPLATE .'.html';

    if (!file_exists($formTemplateFile)) {
        throw new RuntimeException("Form template is unavailable.");
    }

    $content = file_get_contents($formTemplateFile);
    if ($content === false) {
        throw new RuntimeException("Form template could not be read.");
    }

    return $content;
}

try {
    deliverJsWithTranslationsAndPath();
} catch (Throwable $ex) {
    http_response_code(500);
    error_log(
        "Widget delivery failed: "
        . get_class($ex)
        . ": "
        . $ex->getMessage()
    );
    echo INTERNAL_SERVER_ERROR_MESSAGE;
}
