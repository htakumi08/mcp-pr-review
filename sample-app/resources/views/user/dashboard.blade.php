<!doctype html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>利用者画面</title>
</head>
<body>
    <h1>{{ $user->name }}さん、こんにちは</h1>

    <p>
        <a href="{{ route('profile.name') }}">名前を変更</a>
    </p>
    <p>
        <a href="{{ route('profile.password') }}">パスワードを変更</a>
    </p>

    <form method="POST" action="{{ route('logout') }}">
        @csrf
        <button type="submit">ログアウト</button>
    </form>
</body>
</html>
