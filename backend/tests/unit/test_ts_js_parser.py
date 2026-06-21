from app.analysis.languages import Language
from app.analysis.ts_js_parser import TsJsParser


def test_js_parser_extracts_imports_exports_symbols_and_tests() -> None:
    source = '''
import React from "react";
import { makeToken as tokenFactory, validate } from "./token";
import * as api from "../api";
const fs = require("fs");

export function route() {
  return validate(makeToken());
}

const makeToken = (value) => value.trim();

export class AuthRoute {
  handle(req) {
    return api.send(req);
  }
}

describe("route", () => {
  it("validates", () => {
    expect(route()).toBeTruthy();
  });
});
'''

    parsed = TsJsParser().parse("src/routes.test.js", source)

    assert parsed.language == Language.JAVASCRIPT
    assert parsed.errors == []
    assert {item.module for item in parsed.imports} >= {
        "react",
        "./token",
        "../api",
        "fs",
    }
    token_import = next(item for item in parsed.imports if item.module == "./token")
    assert token_import.names == ["makeToken", "validate"]

    symbols = {symbol.qualified_name: symbol for symbol in parsed.symbols}
    assert symbols["route"].symbol_type == "function"
    assert symbols["makeToken"].metadata["assignment"] is True
    assert symbols["AuthRoute"].symbol_type == "class"
    assert symbols["AuthRoute.handle"].symbol_type == "method"

    assert {export.name for export in parsed.exports} >= {
        "route",
        "AuthRoute",
        "describe",
        "it",
        "expect",
    }
    assert {call.name for call in parsed.calls} >= {
        "validate",
        "api.send",
        "describe",
        "it",
        "expect",
    }


def test_typescript_parser_handles_types_and_export_default() -> None:
    source = '''
import type { User } from "./types";

export const parseUser = (value: unknown): User => {
  return value as User;
};

export default parseUser;
'''

    parsed = TsJsParser().parse("src/users.ts", source)

    assert parsed.language == Language.TYPESCRIPT
    assert parsed.errors == []
    assert parsed.imports[0].module == "./types"
    assert "parseUser" in {symbol.simple_name for symbol in parsed.symbols}
    assert {export.name for export in parsed.exports} >= {"parseUser"}


def test_tsx_parser_does_not_crash_on_jsx() -> None:
    source = '''
export function View() {
  return <div onClick={() => test("x", () => expect(true).toBe(true))}>Hi</div>;
}
'''

    parsed = TsJsParser().parse("src/view.tsx", source)

    assert parsed.language == Language.TYPESCRIPT
    assert parsed.errors == []
    assert "View" in {symbol.simple_name for symbol in parsed.symbols}
    assert {"test", "expect"} <= {call.name for call in parsed.calls}


def test_js_parser_reports_parse_errors_without_raising() -> None:
    parsed = TsJsParser().parse("src/broken.js", "function () {")

    assert parsed.language == Language.JAVASCRIPT
    assert parsed.errors
