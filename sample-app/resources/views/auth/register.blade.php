<!doctype html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>アカウント登録</title>
</head>
<body>
    <h1>アカウント登録</h1>

    @if ($errors->any())
        <div>
            <ul>
                @foreach ($errors->all() as $error)
                    <li>{{ $error }}</li>
                @endforeach
            </ul>
        </div>
    @endif

    <form method="POST" action="{{ route('register.post') }}">
        @csrf
        <div>
            <label>名前</label>
            <input type="text" name="name" value="{{ old('name') }}" required>
        </div>
        <div>
            <label>メールアドレス</label>
            <input type="email" name="email" value="{{ old('email') }}" required>
        </div>
        <div>
            <label>パスワード</label>
            <input type="password" name="password" required>
        </div>
        <div>
            <label>確認用パスワード</label>
            <input type="password" name="password_confirmation" required>
        </div>
        <button type="submit">登録</button>
    </form>

    <a href="{{ route('login') }}">ログイン画面へ</a>
</body>
</html>
