<!doctype html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>名前を変更</title>
</head>
<body>
    <h1>名前を変更</h1>

    @if ($errors->any())
        <div>
            @foreach ($errors->all() as $error)
                <li>{{ $error }}</li>
            @endforeach
        </div>
    @endif

    <form method="POST" action="{{ route('profile.name.post') }}">
        @csrf
        <div>
            <label>新しい名前</label>
            <input type="text" name="name" value="{{ old('name', auth()->user()->name) }}" required>
        </div>
        <button type="submit">保存</button>
    </form>

    <a href="{{ route('dashboard') }}">利用者画面へ戻る</a>
</body>
</html>
