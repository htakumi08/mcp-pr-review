<!doctype html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>パスワードを変更</title>
</head>
<body>
    <h1>パスワードを変更</h1>

    <p>新しいパスワードは8文字以上で入力してください。</p>
    <p>現在のパスワードと同じパスワードは設定できません。</p>

    @if ($errors->any())
        <div>
            @foreach ($errors->all() as $error)
                <li>{{ $error }}</li>
            @endforeach
        </div>
    @endif

    <form method="POST" action="{{ route('profile.password.post') }}">
        @csrf
        <div>
            <label>現在のパスワード</label>
            <input type="password" name="current_password" required>
        </div>
        <div>
            <label>新しいパスワード</label>
            <input type="password" name="password" required>
        </div>
        <div>
            <label>新しいパスワード確認入力</label>
            <input type="password" name="password_confirmation" required>
        </div>
        <button type="submit">保存</button>
    </form>

    <a href="{{ route('dashboard') }}">利用者画面へ戻る</a>
</body>
</html>
