import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}));
    const { email, password } = body;

    // Validate demo credentials or any provided email/password
    if (email) {
      const response = NextResponse.json({
        success: true,
        access_token: "jwt_mock_valid_999",
        token: "jwt_mock_valid_999",
        user: {
          id: "usr_admin_001",
          email,
          role: "ADMIN",
          name: "System Administrator",
        },
      });

      response.cookies.set("session_token", "jwt_mock_valid_999", {
        path: "/",
        httpOnly: false,
        maxAge: 86400,
        sameSite: "lax",
      });

      return response;
    }

    return NextResponse.json(
      { error: "Invalid credentials: Email is required." },
      { status: 400 }
    );
  } catch (error: any) {
    return NextResponse.json(
      { error: error?.message || "Internal server error during authentication." },
      { status: 500 }
    );
  }
}

