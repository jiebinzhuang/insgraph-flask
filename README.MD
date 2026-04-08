# CI/CD 统一 AI Code Review 技术方案

## 一、方案概述

本方案将 AI Code Review 能力无缝集成到现有 CI/CD 构建流程中，实现 **PR 提交自动触发代码审查**，零改造团队构建镜像。

**核心价值：**

- **零侵入**：不修改任何团队的构建镜像和构建脚本，通过 Volume 挂载 codereview-agent + CLI 注入 Review 能力
- **统一执行体**：自研 codereview-agent（Go 静态二进制）作为容器内唯一 Review 入口，支持调用 Claude CLI 或 API 直调等多种执行方式
- **大 Diff 分批审查**：变更量超过阈值时自动按文件分批 Review，各批结果智能合并为统一报告
- **安全隔离**：所有 AI 调用在构建容器内完成，API Key 不落盘，容器销毁即清除
- **发布卡点**：Review 结果接入风火轮 CI/CD 流程统一卡点，未通过 Review 的代码不允许发布

---

## 二、整体架构

```mermaid
graph TB
    subgraph Host["各团队构建机（宿主机）"]
        FW["fw-agent<br/>风火轮已有 Agent<br/>（下载代码 / 编译打包）"]
        CRA["/opt/codereview-agent/<br/>codereview-agent 二进制"]
        CLI["/opt/claude-cli/<br/>Claude CLI 二进制"]
        VOL["/data/review/&lt;taskId&gt;/<br/>共享卷"]
    end

    subgraph Container["构建容器（团队原有镜像，零改造）"]
        AGENT["codereview-agent<br/>Review 唯一入口"]
        DISPATCH["引擎调度<br/>（按策略配置）"]

        subgraph ENGINES["执行方式"]
            CLI_CALL["调用 Claude CLI"]
            API_CALL["API 直调<br/>（内置引擎）"]
        end

        BATCH["分批调度器"]
        MERGE["结果合并器"]
        BUILD["编译打包<br/>原有流程不变"]
    end

    FW -->|"1. 获取需求 + 拉取 Skill + 生成 Config"| VOL
    FW -->|"2. 挂载 agent + CLI + 共享卷"| Container
    CRA -.->|":ro 只读挂载"| Container
    CLI -.->|":ro 只读挂载"| Container
    VOL -.->|":rw 读写挂载"| Container

    AGENT -->|"读取 Config"| DISPATCH
    DISPATCH --> BATCH
    BATCH --> ENGINES
    ENGINES --> MERGE
    MERGE -->|"review-result.json"| VOL
    VOL -->|"3. 读取结果"| FW
    FW -->|"4. 上报结果"| REPORT["风火轮 + 敏捷平台"]
    BUILD --> OUTPUT["构建产物"]

    style Host fill:#e8f5e9,stroke:#2e7d32
    style Container fill:#e3f2fd,stroke:#1565c0
    style ENGINES fill:#f3e5f5,stroke:#7b1fa2
    style FW fill:#fff9c4,stroke:#f9a825
    style AGENT fill:#ffccbc,stroke:#bf360c
    style BATCH fill:#fff9c4,stroke:#f9a825
    style MERGE fill:#fff9c4,stroke:#f9a825
```

**架构要点：**
- **fw-agent**：风火轮已有的构建 Agent（负责下载代码、编译打包等），扩展 Review 相关逻辑——准备共享卷、获取敏捷平台需求、拉取 Skill、生成 Config，容器退出后收集结果上报
- **codereview-agent**：新开发的 Go 静态二进制（`CGO_ENABLED=0`），通过 Volume 挂载到容器，是容器内 Review 的唯一执行入口
- **Claude CLI**：同样通过 Volume 只读挂载到容器（不修改原有镜像），供 codereview-agent 调用
- **执行方式可配置**：codereview-agent 根据 review-config.json 中的策略配置，选择调用 Claude CLI 或通过 API 直调执行 Review
- **分批调度 + 结果合并**：大 Diff 自动拆分为多批，逐批执行后合并为统一报告

---

## 三、codereview-agent 设计

codereview-agent 是一个 Go 静态编译的二进制文件，容器内通过共享卷读取配置，执行 Code Review，输出标准化结果。

### 执行方式

```mermaid
flowchart TD
    AGENT(["codereview-agent 启动"]) --> READ["读取 review-config.json<br/>+ Skill 文件"]
    READ --> DIFF["执行 git diff<br/>提取变更"]
    DIFF --> CHECK{"变更量检查"}
    CHECK -->|"0 行"| SKIP["写入 skipped result"]
    CHECK -->|"有变更"| STRATEGY{"执行策略<br/>（按 Config 配置）"}

    STRATEGY -->|"cli 模式"| CLI_MODE["调用 Claude CLI<br/>/opt/claude-cli/claude -p ..."]
    STRATEGY -->|"api 模式"| API_MODE["API 直调<br/>codereview-agent 内置<br/>HTTP Client → Claude API"]

    CLI_MODE --> BATCH_CHECK
    API_MODE --> BATCH_CHECK

    BATCH_CHECK{"需要分批?<br/>（≤ 10 文件 / ≤ 300 行）"}
    BATCH_CHECK -->|"单批"| EXEC_ONE["执行单次 Review"]
    BATCH_CHECK -->|"多批"| EXEC_BATCH["按文件分批<br/>逐批执行 Review"]
    EXEC_BATCH --> MERGE_RESULT["合并各批结果"]

    EXEC_ONE --> OUTPUT["写入 review-result.json<br/>+ review-usage.json"]
    MERGE_RESULT --> OUTPUT

    style AGENT fill:#ffccbc,stroke:#bf360c
    style CLI_MODE fill:#f3e5f5,stroke:#7b1fa2
    style API_MODE fill:#e3f2fd,stroke:#1565c0
    style OUTPUT fill:#e8f5e9,stroke:#2e7d32
```

### 两种执行模式

| 模式 | 调用方式 | 适用场景 | 说明 |
|------|---------|---------|------|
| **CLI 模式** | `os/exec` 调用 `/opt/claude-cli/claude -p "..." --output-format json` | Claude CLI 可运行的环境（glibc ≥ 2.17） | 利用 Claude CLI 完整能力，输出结构化 JSON |
| **API 模式** | codereview-agent 内置 HTTP Client，直接调用 Claude API | CLI 不可运行的环境，或需要精细控制（多模型编排等） | codereview-agent 自建 Tool Use 循环，支持未来扩展 Codex / Gemini API |

**模式选择策略：**
1. 按 `review-config.json` 中的 `engineMode` 配置优先
2. 未指定时自动探测：检测 Claude CLI 是否可执行（`/opt/claude-cli/claude --version`），可执行则用 CLI 模式，否则降级到 API 模式

### codereview-agent 调用方式

```bash
/opt/codereview-agent/codereview-agent \
    --config /review/config/review-config.json \
    --output-dir /review/output/
```

codereview-agent 内部完成所有工作：git diff → 语言探测 → Skill 选择 → 分批策略 → 调用引擎 → 结果合并 → 写入 result/usage JSON。

---

## 四、核心流程

### 一次 Code Review 的完整生命周期

```mermaid
flowchart TD
    START(["构建任务到达"]) --> CHECK{"enableReview<br/>== true ?"}
    CHECK -->|No| BUILD_ONLY["直接构建<br/>（跳过 Review）"]
    CHECK -->|Yes| PREPARE

    subgraph PREPARE["Phase: 准备阶段（fw-agent）"]
        P1["创建共享卷目录"]
        P2["获取敏捷平台需求<br/>（关联需求描述、验收标准等）"]
        P3["拉取 Skill<br/>（合并公司级、部门级、应用级 Skill）"]
        P4["获取 API Key"]
        P5["review所需环境、环境准备<br/>（部分从风火轮平台获取，含引擎策略配置）"]
        P1 --> P2 --> P3 --> P4 --> P5
    end

    PREPARE --> LAUNCH["启动构建容器<br/>挂载 codereview-agent<br/>+ Claude CLI + 共享卷"]

    subgraph EXEC["Phase: 执行阶段（容器内 codereview-agent）"]
        E1["git diff 提取变更"]
        E2{"Diff 检查"}
        E3["语言探测 + 选择 Skill"]
        E4["选择执行模式<br/>（CLI / API，按策略配置）"]
        E5{"变更量 ≤ 阈值?"}

        E6_SINGLE["单批执行 Review"]
        E6_BATCH["按文件分批<br/>逐批执行 Review"]
        E7_BATCH["合并各批结果<br/>Issue 去重 / Score 汇总"]
        E8["写入 result.json + usage.json"]

        E1 --> E2
        E2 -->|"0 行"| SKIP["跳过: no_diff"]
        E2 -->|"有变更"| E3 --> E4 --> E5
        E5 -->|"是"| E6_SINGLE --> E8
        E5 -->|"否"| E6_BATCH --> E7_BATCH --> E8
    end

    LAUNCH --> EXEC

    subgraph COLLECT["Phase: 收集阶段（fw-agent）"]
        C1["读取 review-result.json"]
        C2["读取 review-usage.json"]
        C3["校验 JSON 结构"]
        C1 --> C3
        C2 --> C3
    end

    EXEC --> COLLECT

    COLLECT --> REPORT["上报结果<br/>风火轮 + 敏捷平台"]
    REPORT --> CLEANUP["清理共享卷<br/>临时目录"]
    CLEANUP --> DONE(["完成"])

    BUILD_ONLY --> DONE
    SKIP --> COLLECT

    style PREPARE fill:#e8f5e9,stroke:#2e7d32
    style EXEC fill:#e3f2fd,stroke:#1565c0
    style COLLECT fill:#fff3e0,stroke:#e65100
```

### 分批 Review 与报告合并

当变更量超过阈值时，codereview-agent 自动进入分批模式：

```mermaid
flowchart LR
    DIFF["完整 Diff<br/>25 文件 / 800 行"] --> SPLIT["按文件拆分"]
    SPLIT --> B1["Batch 1<br/>文件 1-8"]
    SPLIT --> B2["Batch 2<br/>文件 9-16"]
    SPLIT --> B3["Batch 3<br/>文件 17-25"]

    B1 --> R1["Review 结果 1"]
    B2 --> R2["Review 结果 2"]
    B3 --> R3["Review 结果 3"]

    R1 --> MERGE["报告合并器"]
    R2 --> MERGE
    R3 --> MERGE

    MERGE --> FINAL["统一报告<br/>review-result.json"]

    style DIFF fill:#e3f2fd,stroke:#1565c0
    style MERGE fill:#ffccbc,stroke:#bf360c
    style FINAL fill:#e8f5e9,stroke:#2e7d32
```

**报告合并策略：**

| 维度 | 合并规则 |
|------|---------|
| **Issues** | 各批 Issues 汇总，按 file + line 去重，保留 confidence 更高的条目 |
| **Score** | 各批 Score 按变更行数加权平均 |
| **Summary** | 基于各批 Summary 生成整体摘要 |
| **Usage** | inputTokens / outputTokens / costUsd 各批累加 |
| **Status** | 全部成功 → `completed`；部分失败 → `partial`（已完成批次结果仍保留上报） |

---

## 五、触发机制

```mermaid
flowchart LR
    subgraph AUTO["自动触发"]
        PM["敏捷管理平台<br/>自动创建 Code Review"] -->|"调用风火轮<br/>Code Review 流程"| FH["风火轮"]
    end

    subgraph MANUAL["手动触发"]
        direction TB
        USER1["用户选择分支"] --> UI["风火轮 UI"]
        UI --> FH
        USER2["用户客户端<br/>IDE / CLI"] --> MCP["MCP Server<br/>（风火轮 Code Review）"]
        MCP --> FH
    end

    FH -->|"构建任务<br/>enableReview=true"| FWA["fw-agent"]
    FWA --> REVIEW["执行 Code Review"]

    style AUTO fill:#e3f2fd,stroke:#1565c0
    style MANUAL fill:#fff3e0,stroke:#e65100
    style MCP fill:#f3e5f5,stroke:#7b1fa2
```

| 触发方式 | 触发源 | 参数来源 |
|---------|--------|---------|
| **自动触发** | 敏捷管理平台自动创建 Code Review → 调用风火轮 Code Review 流程 | `sourceBranch`、`targetBranch`、`prUrl` 自动填充 |
| **手动触发 — UI** | 用户在风火轮 UI 选择项目和分支，点击"Code Review" | 用户手动选择源/目标分支 |
| **手动触发 — MCP** | 用户在客户端（IDE / Claude CLI）通过 MCP Server 调用风火轮 Code Review | 客户端自动获取当前项目、分支信息，通过 MCP 协议传递 |

---

## 六、数据交换协议

fw-agent 与构建容器之间通过**共享卷（Shared Volume）**进行数据交换，纯文件协议，无网络通信。

### 共享卷目录结构

```
/data/review/<taskId>/
├── config/
│   ├── review-config.json       ← fw-agent 写入，codereview-agent 读取
│   └── skills/                  ← fw-agent 写入，codereview-agent 读取
│       ├── general-code-review.md
│       └── java-review.md
└── output/
    ├── diff.patch               ← codereview-agent 写入
    ├── review-result.json       ← codereview-agent 写入，fw-agent 读取（核心结果）
    └── review-usage.json        ← codereview-agent 写入，fw-agent 读取（用量统计）
```

### 数据流向

```mermaid
sequenceDiagram
    participant FW as fw-agent（风火轮已有）
    participant VOL as 共享卷
    participant CT as 构建容器
    participant CRA as codereview-agent

    FW->>VOL: 写入 review-config.json（含引擎策略 + API Key）
    FW->>VOL: 写入 Skill 文件
    FW->>CT: 启动容器（挂载 codereview-agent + Claude CLI + 共享卷）
    CRA->>VOL: 读取 Config + Skill
    CRA->>CRA: git diff → 提取变更
    CRA->>CRA: 语言探测 → 选择 Skill → 确定执行模式
    alt 单批
        CRA->>CRA: 调用 Claude CLI 或 API 直调
    else 多批
        CRA->>CRA: 按文件分批 → 逐批调用引擎
        CRA->>CRA: 合并各批结果
    end
    CRA->>VOL: 写入 review-result.json
    CRA->>VOL: 写入 review-usage.json
    CT-->>FW: 容器退出
    FW->>VOL: 读取 Result + Usage
    FW->>FW: 上报结果 + 清理临时目录
```

### review-result.json

```json
{
  "status": "completed",
  "engineMode": "cli",
  "summary": "本次变更涉及 8 个文件，发现 2 个安全风险",
  "score": 78,
  "issues": [
    {
      "file": "src/main/java/com/xxx/UserService.java",
      "line": 42,
      "severity": "error",
      "category": "security",
      "message": "SQL 字符串拼接存在注入风险",
      "suggestion": "使用 MyBatis #{} 参数绑定",
      "confidence": "high"
    }
  ],
  "errorCount": 2,
  "warningCount": 3,
  "suggestionCount": 5,
  "batches": [
    {
      "batchId": 1,
      "files": ["UserService.java", "AuthController.java"],
      "status": "completed",
      "issueCount": 2,
      "score": 75
    },
    {
      "batchId": 2,
      "files": ["OrderService.java", "PaymentService.java"],
      "status": "completed",
      "issueCount": 3,
      "score": 80
    }
  ]
}
```

> `batches` 字段仅在分批 Review 时出现，单批时为 `null`。

---

## 七、Skill 体系

Skill 是可配置的 Review 规则集，以 Markdown 文件形式管理，由研发工作台统一维护。

```mermaid
graph TD
    subgraph SKILL["Review Skill 体系"]
        GENERAL["通用基础<br/>general-code-review.md<br/>所有项目必用"]
        JAVA["Java 专项<br/>Spring Boot / MyBatis / 并发"]
        GO["Go 专项<br/>error handling / goroutine"]
        FE["前端专项<br/>XSS / 组件设计 / 状态管理"]
        PY["Python 专项<br/>类型安全 / 资源管理"]
        SEC["安全专项<br/>security-review.md<br/>可叠加"]
        TEAM["团队自定义<br/>team-xxx-review.md"]
    end

    DETECT{"语言探测"} -->|pom.xml| JAVA
    DETECT -->|go.mod| GO
    DETECT -->|package.json| FE
    DETECT -->|requirements.txt| PY
    DETECT -->|"兜底"| GENERAL

    style GENERAL fill:#e8f5e9,stroke:#2e7d32
    style SEC fill:#ffcdd2,stroke:#c62828
    style TEAM fill:#fff9c4,stroke:#f9a825
```

**Skill 选择策略：**

| 优先级 | 条件 | 行为 |
|-------|------|------|
| 1 | 指定 `skillId` | 直接使用指定 Skill |
| 2 | 指定 `language` | 匹配对应语言 Skill |
| 3 | 都未指定 | 自动探测项目文件（pom.xml / go.mod / package.json）→ 选择对应 Skill |
| 4 | 探测失败 | 使用通用 Skill（general-code-review.md） |

**Skill 缓存策略：** fw-agent 作为常驻进程，启动时全量拉取 Skill 并缓存到本地磁盘，每 5 分钟增量刷新。构建时从缓存读取，研发工作台 API 不可达时使用本地缓存兜底。

---

## 八、执行模式配置

codereview-agent 支持两种执行模式，通过 `review-config.json` 中的策略灵活配置。

```mermaid
graph LR
    CONFIG["review-config.json"] --> CRA{"codereview-agent"}
    CRA -->|"engineMode: cli"| CLI["调用 Claude CLI<br/>/opt/claude-cli/claude -p ..."]
    CRA -->|"engineMode: api"| API["API 直调<br/>内置 HTTP Client<br/>→ Claude API"]
    CRA -->|"engineMode: auto"| AUTO["自动探测<br/>CLI 可用则用 CLI<br/>否则降级 API"]

    style CRA fill:#ffccbc,stroke:#bf360c
    style CLI fill:#f3e5f5,stroke:#7b1fa2
    style API fill:#e3f2fd,stroke:#1565c0
    style AUTO fill:#fff9c4,stroke:#f9a825
```

### 模式对比

| 模式 | 调用方式 | 环境要求 | 适用场景 |
|------|---------|---------|---------|
| **CLI** | `os/exec` 调用 Claude CLI | glibc ≥ 2.17 | CLI 可运行的标准构建镜像 |
| **API** | codereview-agent 内置 HTTP Client 直调 API | **无额外依赖** | CLI 无法运行的精简镜像（alpine/musl），或需精细控制（多模型编排等） |
| **auto**（默认） | 自动探测 CLI 可用性，优先 CLI，不可用则降级 API | — | 通用默认策略 |

### review-config.json 配置示例

```json
{
  "version": "1.0",
  "taskId": "build-12345",
  "projectName": "user-service",
  "triggerType": "pr",
  "sourceBranch": "feature/add-auth",
  "targetBranch": "main",
  "engineMode": "auto",
  "model": "claude-sonnet-4-6",
  "apiKey": "sk-ant-...",
  "skillFile": "config/skills/java-review.md",
  "outputDir": "output/",
  "batchThreshold": {
    "maxFiles": 10,
    "maxLines": 300
  },
  "timeoutSeconds": 300,
  "prUrl": "https://bitbucket.example.com/.../pull-requests/123"
}
```

---

## 九、错误处理与发布卡点

**核心原则：Review 异常不阻断构建，但 Review 结果作为发布卡点 — 未通过 Review 的代码不允许发布。**

```mermaid
flowchart TD
    ERR(["异常发生"]) --> TYPE{"异常类型"}

    TYPE -->|"Skill API 不可达"| A["使用本地缓存<br/>无缓存则跳过 Review"]
    TYPE -->|"API Key 无效"| B["跳过 Review"]
    TYPE -->|"Review 引擎超时"| C["timeout 杀进程<br/>写 error result"]
    TYPE -->|"引擎非零退出"| D["写 error result"]
    TYPE -->|"Result JSON 缺失/异常"| E["fw-agent 记 warning<br/>上报空结果"]
    TYPE -->|"Diff 为空"| F["status=skipped<br/>reason=no_diff"]
    TYPE -->|"部分批次失败"| G["status=partial<br/>已完成批次结果仍上报"]

    A --> CONTINUE["构建继续<br/>Review 状态上报"]
    B --> CONTINUE
    C --> CONTINUE
    D --> CONTINUE
    E --> CONTINUE
    F --> CONTINUE
    G --> CONTINUE

    CONTINUE --> GATE{"风火轮发布卡点"}
    GATE -->|"Review 通过"| DEPLOY["允许发布"]
    GATE -->|"Review 未通过<br/>或未完成"| BLOCK["阻断发布<br/>需人工处理"]

    style ERR fill:#ffcdd2,stroke:#c62828
    style CONTINUE fill:#fff9c4,stroke:#f9a825
    style GATE fill:#e3f2fd,stroke:#1565c0
    style DEPLOY fill:#e8f5e9,stroke:#2e7d32
    style BLOCK fill:#ffcdd2,stroke:#c62828
```

**卡点规则：**
- 构建阶段：Review 异常不阻断构建，确保构建产物正常产出
- 发布阶段：风火轮 CI/CD 流程统一卡点判断，Review 状态为 `completed` 且无 `error` 级别 Issue 时方可发布
- Review 跳过或失败的代码，需人工确认后才能放行发布

---

## 十、关键设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| **codereview-agent 语言** | Go（`CGO_ENABLED=0` 静态编译） | 零依赖，兼容所有构建镜像（alpine/debian/centos/distroless） |
| **CLI 挂载方式** | Volume 只读挂载（不改镜像） | 避免修改各团队构建镜像，后续维护成本低 |
| **执行模式** | CLI + API 双模式，自动降级 | CLI 可用时利用其完整能力；不可用时 API 直调兜底 |
| **Skill 拉取位置** | fw-agent 宿主机 | fw-agent 已集成 DNA SDK，常驻进程可缓存，容器启动前预备完成 |
| **通信方式** | 共享卷（文件协议） | 无网络通信，简单可靠 |
| **Diff 策略** | 三点 diff（target...HEAD） | 只显示源分支增量变更，排除 lock 文件和 vendor 目录 |
| **分批阈值** | 默认 ≤ 10 文件 / ≤ 300 行 | 可通过 `batchThreshold` 配置调整 |
| **超时策略** | 默认 5 分钟 / 批 | 覆盖绝大多数 Review 场景，超时自动杀进程 |

---

## 十一、接口概览

### 研发工作台 DNA RPC 接口

| 接口 | 用途 | 调用方 |
|------|------|--------|
| `ReviewSkillService.ListSkills` | 获取 Skill 列表 | fw-agent |
| `ReviewSkillService.GetSkill` | 获取 Skill 内容 | fw-agent |
| `ReviewSkillService.ResolveSkill` | 按项目/语言/团队智能解析 Skill | fw-agent |
| `ReviewKeyService.GetTemporaryKey` | 获取临时 API Key | fw-agent |
| `ReviewUsageService.ReportUsage` | 上报 Review 用量 | fw-agent |

### 构建任务参数扩展

风火轮下发的构建任务新增 `review` 字段：

```json
{
  "taskId": "build-12345",
  "review": {
    "enableReview": true,
    "triggerType": "pr",
    "engineMode": "auto",
    "sourceBranch": "feature/add-auth",
    "targetBranch": "main",
    "prUrl": "https://bitbucket.example.com/.../pull-requests/123",
    "skillId": "",
    "language": "java",
    "maxWaitSeconds": 300
  }
}
```

### 容器挂载配置

fw-agent 启动构建容器时新增的 Volume 挂载：

```
-v /opt/codereview-agent:/opt/codereview-agent:ro    ← codereview-agent 二进制
-v /opt/claude-cli:/opt/claude-cli:ro                ← Claude CLI 二进制
-v /data/review/<taskId>:/review:rw                  ← 共享卷（Config + Result）
```

容器内 Review 执行命令：

```bash
/opt/codereview-agent/codereview-agent \
    --config /review/config/review-config.json \
    --output-dir /review/output/
```
