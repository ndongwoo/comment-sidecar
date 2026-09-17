<?php
ob_start("ob_gzhandler");
include_once __DIR__ . "/config.php";

function connect() {
    $handler = new PDO("mysql:host=".DB_HOST.";port=".DB_PORT.";dbname=".DB_NAME.";charset=utf8mb4", DB_USER, DB_PW);
    $handler->setAttribute( PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION );
    $handler->setAttribute( PDO::ATTR_STRINGIFY_FETCHES, true );
    return $handler;
}

function readTranslations(): array  {
    $translationFile = __DIR__ . '/translations/'. LANGUAGE .'.php';
    if (!file_exists($translationFile)) {
        http_response_code(500);
        echo "Can't find translation file $translationFile";
        return [];
    }
    include $translationFile;
    return $translations;
}

class InvalidRequestException extends Exception {}
class ForbiddenRequestException extends Exception {}

const INTERNAL_SERVER_ERROR_MESSAGE = "Internal server error.";

function sendJsonErrorResponse(Throwable $ex) {
    header('Content-Type: application/json; charset=UTF-8');

    if ($ex instanceof ForbiddenRequestException) {
        http_response_code(403);
        $message = $ex->getMessage();
    } elseif ($ex instanceof InvalidRequestException) {
        http_response_code(400);
        $message = $ex->getMessage();
    } else {
        http_response_code(500);
        error_log("Unhandled ".get_class($ex).": ".$ex->getMessage());
        $message = INTERNAL_SERVER_ERROR_MESSAGE;
    }

    echo json_encode([ "message" => $message ], JSON_UNESCAPED_UNICODE);
}
