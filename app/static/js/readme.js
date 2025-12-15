// README 마크다운 렌더링 및 목차 네비게이션

// 제목 텍스트를 id로 변환하는 함수 (GitHub 스타일, 한글 지원)
function slugify(text) {
    return text
        .toString()
        .toLowerCase()
        .trim()
        .replace(/\./g, '')             // 점 제거 (예: "1. 필수 요구사항" → "1 필수 요구사항")
        .replace(/\s+/g, '-')           // 공백을 하이픈으로
        .replace(/[^\w\-가-힣0-9]+/g, '')   // 특수문자 제거 (한글, 숫자, 하이픈 유지)
        .replace(/\-\-+/g, '-')         // 연속된 하이픈을 하나로
        .replace(/^-+/, '')             // 시작 하이픈 제거
        .replace(/-+$/, '');            // 끝 하이픈 제거
}

// README 마크다운 렌더링 및 목차 링크 처리
function renderReadme(readmeMarkdown) {
    if (!readmeMarkdown) {
        document.getElementById('readme-content').innerHTML = '<p>README 내용이 없습니다.</p>';
        return;
    }

    // marked 옵션 설정
    marked.setOptions({
        headerIds: true,
        mangle: false
    });

    const htmlContent = marked.parse(readmeMarkdown);
    const readmeContent = document.getElementById('readme-content');
    readmeContent.innerHTML = htmlContent;

    // 모든 제목에 id 추가 (한글 제목 지원)
    const headings = readmeContent.querySelectorAll('h1, h2, h3, h4, h5, h6');
    const headingMap = new Map(); // 제목 ID 매핑 저장

    headings.forEach(heading => {
        const text = heading.textContent.trim();
        const id = slugify(text);
        heading.id = id;
        headingMap.set(id, heading);
        headingMap.set(text.toLowerCase(), heading); // 텍스트로도 저장
    });

    // 모든 앵커 링크 수정 및 클릭 이벤트 처리
    const links = readmeContent.querySelectorAll('a[href^="#"]');
    links.forEach(link => {
        const href = link.getAttribute('href');
        if (href && href.startsWith('#')) {
            // 각 링크의 href와 linkText를 클로저로 캡처 (값으로)
            const originalTargetId = href.substring(1);
            const linkText = link.textContent.trim();

            // URL 디코딩된 targetId를 미리 계산하여 캡처
            let decodedTargetId = originalTargetId;
            try {
                decodedTargetId = decodeURIComponent(originalTargetId);
            } catch (e) {
                // 디코딩 실패 시 원본 사용
            }

            // 각 링크마다 고유한 값을 캡처하기 위해 즉시 실행 함수 사용
            (function(capturedTargetId, capturedLinkText) {
                // 링크 클릭 이벤트
                link.addEventListener('click', function(e) {
                    e.preventDefault();

                    let targetElement = null;

                    // 1. URL 디코딩된 ID로 직접 찾기
                    targetElement = document.getElementById(capturedTargetId);

                    // 2. Map에서 ID로 찾기
                    if (!targetElement && headingMap.has(capturedTargetId)) {
                        targetElement = headingMap.get(capturedTargetId);
                    }

                    // 3. 링크 텍스트를 slugify해서 Map에서 찾기
                    if (!targetElement) {
                        const linkId = slugify(capturedLinkText);
                        if (headingMap.has(linkId)) {
                            targetElement = headingMap.get(linkId);
                        }
                    }

                    // 4. 링크 텍스트로 직접 찾기 (대소문자 무시)
                    if (!targetElement && headingMap.has(capturedLinkText.toLowerCase())) {
                        targetElement = headingMap.get(capturedLinkText.toLowerCase());
                    }

                    // 5. 모든 제목을 순회하며 정확히 매칭
                    if (!targetElement) {
                        const headings = readmeContent.querySelectorAll('h1, h2, h3, h4, h5, h6');
                        for (let i = 0; i < headings.length; i++) {
                            const heading = headings[i];
                            const headingText = heading.textContent.trim();
                            const headingId = slugify(headingText);

                            // 여러 방법으로 매칭 시도
                            if (headingId === capturedTargetId ||
                                headingId === slugify(capturedLinkText) ||
                                headingText.toLowerCase() === capturedLinkText.toLowerCase() ||
                                headingText === capturedLinkText) {
                                targetElement = heading;
                                break;
                            }
                        }
                    }

                    if (targetElement) {
                        // 부드러운 스크롤
                        const yOffset = -20;
                        const y = targetElement.getBoundingClientRect().top + window.pageYOffset + yOffset;
                        window.scrollTo({ top: y, behavior: 'smooth' });
                    }
                });
            })(decodedTargetId, linkText); // 값으로 전달하여 캡처
        }
    });
}

