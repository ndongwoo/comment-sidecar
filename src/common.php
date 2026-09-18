<?php
ob_start("ob_gzhandler");
include_once __DIR__ . "/config.php";

function connect() {
    $handler = new PDO("mysql:host=".DB_HOST.";port=".DB_PORT.";dbname=".DB_NAME.";charset=utf8mb4", DB_USER, DB_PW);
    $handler->setAttribute( PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION );
    $handler->setAttribute( PDO::ATTR_STRINGIFY_FETCHES, true );
    return $handler;
}

function normalizeTranslationLanguage($language): ?string {
    if (!is_string($language)) {
        return null;
    }

    $language = strtolower(str_replace('_', '-', trim($language)));
    if ($language === ''
        || preg_match('/^[a-z]{2,8}(?:-[a-z0-9]{2,8})*$/D', $language) !== 1) {
        return null;
    }

    return $language;
}

function translationLanguageCandidates(string $language): array {
    $parts = explode('-', $language, 2);
    if (count($parts) === 1) {
        return [$language];
    }

    return [$language, $parts[0]];
}

function translationResourceExists(string $language): bool {
    return file_exists(__DIR__ . '/translations/' . $language . '.php');
}

function resolveTranslationLanguage($requestedLanguage = null): string {
    $requested = normalizeTranslationLanguage($requestedLanguage);
    if ($requested !== null) {
        foreach (translationLanguageCandidates($requested) as $candidate) {
            if (translationResourceExists($candidate)) {
                return $candidate;
            }
        }
    }

    $configured = normalizeTranslationLanguage(LANGUAGE);
    if ($configured === null) {
        throw new RuntimeException("Configured language is invalid.");
    }

    foreach (translationLanguageCandidates($configured) as $candidate) {
        if (translationResourceExists($candidate)) {
            return $candidate;
        }
    }

    throw new RuntimeException("Configured translation resource is unavailable.");
}

function readTranslations($language = null): array {
    $resolvedLanguage = resolveTranslationLanguage($language);
    $translationFile = __DIR__ . '/translations/' . $resolvedLanguage . '.php';

    include $translationFile;

    if (!isset($translations) || !is_array($translations)) {
        throw new RuntimeException("Translation resource is invalid.");
    }

    return $translations;
}

class InvalidRequestException extends Exception {}
class ForbiddenRequestException extends Exception {}

function ipMatchesCidr($ip, $cidr): bool {
    if (!is_string($ip) || trim($ip) === '') {
        throw new InvalidArgumentException("IP address must be a non-empty string.");
    }
    if (!is_string($cidr) || trim($cidr) === '') {
        throw new InvalidArgumentException("CIDR must be a non-empty string.");
    }

    $parts = explode('/', trim($cidr), 2);
    if (count($parts) !== 2) {
        throw new InvalidArgumentException("CIDR prefix is required.");
    }

    [$network, $prefixText] = $parts;
    $network = trim($network);
    $prefixText = trim($prefixText);

    if (preg_match('/^[0-9]+$/D', $prefixText) !== 1) {
        throw new InvalidArgumentException("CIDR prefix must be numeric.");
    }

    $packedIp = inet_pton(trim($ip));
    $packedNetwork = inet_pton($network);

    if ($packedIp === false) {
        throw new InvalidArgumentException("Invalid IP address.");
    }
    if ($packedNetwork === false) {
        throw new InvalidArgumentException("Invalid CIDR network address.");
    }

    if (strlen($packedIp) !== strlen($packedNetwork)) {
        return false;
    }

    $maxBits = strlen($packedIp) * 8;
    $prefix = (int) $prefixText;
    if ($prefix < 0 || $prefix > $maxBits) {
        throw new InvalidArgumentException("CIDR prefix is out of range.");
    }

    $fullBytes = intdiv($prefix, 8);
    $remainingBits = $prefix % 8;

    if ($fullBytes > 0
        && substr($packedIp, 0, $fullBytes)
            !== substr($packedNetwork, 0, $fullBytes)) {
        return false;
    }

    if ($remainingBits === 0) {
        return true;
    }

    $mask = (0xFF << (8 - $remainingBits)) & 0xFF;

    return (ord($packedIp[$fullBytes]) & $mask)
        === (ord($packedNetwork[$fullBytes]) & $mask);
}

function enforceClientIpBlocklist() {
    $clientIp = $_SERVER['REMOTE_ADDR'] ?? null;

    if (!is_string($clientIp)
        || trim($clientIp) === ''
        || inet_pton(trim($clientIp)) === false) {
        throw new RuntimeException("Client IP address is unavailable.");
    }

    foreach (BLOCKED_IP_CIDRS as $cidr) {
        if (!is_string($cidr)) {
            throw new RuntimeException(
                "BLOCKED_IP_CIDRS contains an invalid entry."
            );
        }

        try {
            $blocked = ipMatchesCidr($clientIp, $cidr);
        } catch (InvalidArgumentException $ex) {
            throw new RuntimeException(
                "BLOCKED_IP_CIDRS contains an invalid CIDR.",
                0,
                $ex
            );
        }

        if ($blocked) {
            throw new ForbiddenRequestException(
                "Comment posting is not allowed from this network."
            );
        }
    }
}

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
