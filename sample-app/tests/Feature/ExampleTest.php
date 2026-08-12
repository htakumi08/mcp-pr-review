<?php

namespace Tests\Feature;

// use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ExampleTest extends TestCase
{
    /**
     * 未認証利用者がトップページからログイン画面へ案内されることを確認する。
     * 認証前に利用者画面を表示しない導線を維持するために必要なテスト。
     */
    public function test_guest_is_redirected_to_login_from_home(): void
    {
        $response = $this->get('/');

        $response->assertRedirectToRoute('login');
    }
}
