import { NextResponse, type NextRequest } from "next/server";
import { COOKIE_TOKEN } from "@/lib/session";

export function middleware(req: NextRequest) {
  if (!req.cookies.get(COOKIE_TOKEN)) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    return NextResponse.redirect(url);
  }
}

export const config = { matcher: ["/((?!login|bff|_next|favicon.ico).*)"] };
