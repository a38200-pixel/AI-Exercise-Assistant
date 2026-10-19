# Changelog

이 문서는 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따르며,
버전은 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

## [Unreleased]

### Added

### Changed
- 스쿼트 횟수를 라벨 전이(`stand → squat → stand`)가 아니라 **무릎각 시계열의 반복 구간**으로 셉니다. 걷기·제자리 걸음처럼 짧은 굴곡과 런지처럼 양발이 앞뒤로 벌어진 동작은 세지 않습니다.
- **측면에서 서 있을 때만** 스쿼트를 셉니다. 정면·사선에서는 횟수가 올라가지 않으며, 추적이 2초 넘게 시작되지 않으면 화면에 사유별 안내("카메라 쪽으로 옆모습이 보이게 서주세요" / "발끝까지 화면에 들어오게 서주세요")가 나타납니다.
- 의자·박스를 이용한 앉았다 일어나기도 스쿼트로 셀 수 있습니다(알려진 한계).
- 설정 `USE_REP_TRACKER`(기본 True)를 False로 하면 이전(v0.1.x)의 라벨 전이 방식으로 셉니다.

### Removed
