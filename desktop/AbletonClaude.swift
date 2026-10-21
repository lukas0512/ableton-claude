import SwiftUI
import AppKit

enum StudioStyle {
    static let background = Color(red: 0.045, green: 0.050, blue: 0.067)
    static let panel = Color(red: 0.072, green: 0.079, blue: 0.10)
    static let accent = Color(red: 0.69, green: 0.60, blue: 1)
    static let line = Color.white.opacity(0.075)
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    var model: AppModel?
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        MainActor.assumeIsolated {
            if model?.training == true || model?.chatRunning == true {
                let alert = NSAlert()
                alert.messageText = "Há uma operação em andamento"
                alert.informativeText = "Ao fechar, a operação será interrompida. As análises já concluídas ficam salvas para retomar depois."
                alert.addButton(withTitle: "Continuar no app"); alert.addButton(withTitle: "Encerrar")
                if alert.runModal() == .alertFirstButtonReturn { return .terminateCancel }
            }
            model?.stop()
            return .terminateNow
        }
    }
}

struct StatusPill: View {
    let title: String
    let good: Bool
    var body: some View {
        HStack(spacing: 7) {
            Circle().fill(good ? Color.green : Color.orange).frame(width: 6, height: 6)
            Text(title).font(.system(size: 12, weight: .medium))
        }.padding(.horizontal, 11).padding(.vertical, 7).background(Color.white.opacity(0.045), in: Capsule())
    }
}

struct Panel<Content: View>: View {
    @ViewBuilder var content: () -> Content
    var body: some View {
        VStack(alignment: .leading, spacing: 16, content: content)
            .frame(maxWidth: .infinity, alignment: .leading).padding(22)
            .background(StudioStyle.panel, in: RoundedRectangle(cornerRadius: 16))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(StudioStyle.line))
    }
}

struct ContentView: View {
    @ObservedObject var model: AppModel
    @State private var showGuide = false
    private let stepNames = ["Boas-vindas", "Conectar ao Live", "Seus samples", "Escolher sua IA", "Ensinar seu som", "Tudo pronto"]
    var body: some View {
        HStack(spacing: 0) {
            sidebar.frame(width: 220)
            Rectangle().fill(StudioStyle.line).frame(width: 1)
            VStack(spacing: 0) {
                if !model.loaded {
                    Spacer(); ProgressView("Preparando seu estúdio…"); Spacer()
                } else if !model.onboardingComplete {
                    onboarding
                } else {
                    studioHeader
                    if model.route == "studio" { StudioView(model: model) }
                    if model.route == "library" {
                        ScrollView { VStack(alignment: .leading, spacing: 24) {
                            title("Sua biblioteca musical", subtitle: "Aprenda novos gêneros sem perder os perfis que você já criou.")
                            LearningView(model: model)
                        }.padding(32) }
                    }
                    if model.route == "settings" {
                        ScrollView { VStack(alignment: .leading, spacing: 24) {
                            title("Conexão e assistente", subtitle: "Escolha a IA que conversa com seu projeto e mantenha a conexão local com o Ableton.")
                            AssistantView(model: model)
                            SamplesView(model: model)
                            LiveSetupView(model: model)
                        }.padding(32) }
                    }
                }
                notices
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }.background(StudioStyle.background).tint(StudioStyle.accent).preferredColorScheme(.dark)
            .frame(minWidth: 1060, minHeight: 720)
            .alert("Você está usando seu plano ChatGPT", isPresented: $model.showPlanWelcome) {
                Button("Entendido", action: model.acknowledgePlan)
            } message: {
                Text("As solicitações elegíveis deste app usam seu plano ou seus créditos ChatGPT. Você pode revisar o uso e os limites nas configurações do ChatGPT.")
            }
            .sheet(isPresented: $showGuide) {
                VStack(alignment: .leading, spacing: 22) {
                    title("Seu processo de produção", subtitle: "Da referência à próxima versão do projeto.")
                    ForEach(Array(["Escolha Criar do zero ou Continuar projeto. Abra um set vazio ou uma cópia no Live.",
                                   "Selecione um gênero aprendido. Ele orienta ritmo, timbre, estrutura e mix.",
                                   "Descreva seu objetivo no chat. O produtor consulta o projeto pelas ferramentas locais.",
                                   "Do zero: escolha 4, 8 ou 16 compassos e construa um motivo com uma base simples.",
                                   "Projeto existente: escolha diagnóstico, groove, arranjo ou mix; preserve a identidade da track.",
                                   "Revise e aplique a proposta. Clique em Ouvir e só aprove o loop quando gostar do resultado.",
                                   "Desenvolva o groove, ouça e aprove. Só então abra o arranjo, reutilizando o material aprovado.",
                                   "Renderize um trecho, compare com suas referências e escute o resultado.",
                                   "Salve no Ableton com ⌘S. Guarde e troque de projeto para retomar as etapas depois."].enumerated()), id: \.offset) { index, text in
                        HStack(alignment: .top, spacing: 14) {
                            Text(String(index + 1)).font(.headline).foregroundStyle(StudioStyle.accent).frame(width: 24)
                            Text(text).fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    Button("Voltar ao estúdio") { showGuide = false }.buttonStyle(.borderedProminent)
                }.padding(32).frame(width: 590).preferredColorScheme(.dark)
            }
    }

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 30) {
            HStack(spacing: 10) {
                Image(systemName: "waveform.path").font(.system(size: 26, weight: .medium)).foregroundStyle(StudioStyle.accent)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Ableton Claude").font(.system(size: 16, weight: .semibold))
                    Text("SEU ESTÚDIO COM IA").font(.system(size: 9, weight: .medium)).tracking(1.5).foregroundStyle(.secondary)
                }
            }.padding(.top, 12)
            if !model.onboardingComplete {
                VStack(alignment: .leading, spacing: 23) {
                    Text("COMECE AQUI").font(.system(size: 10, weight: .semibold)).tracking(1.8).foregroundStyle(.secondary)
                    ForEach(Array(stepNames.enumerated()), id: \.offset) { index, name in
                        HStack(spacing: 11) {
                            ZStack {
                                Circle().fill(index <= model.step ? StudioStyle.accent.opacity(0.17) : Color.white.opacity(0.05)).frame(width: 25, height: 25)
                                if index < model.step { Image(systemName: "checkmark").font(.system(size: 10, weight: .bold)) }
                                else { Text(String(index + 1)).font(.system(size: 11, weight: .semibold)) }
                            }.foregroundStyle(index <= model.step ? StudioStyle.accent : Color.gray)
                            Text(name).font(.system(size: 13, weight: index == model.step ? .semibold : .regular))
                                .foregroundStyle(index == model.step ? Color.white : Color.gray)
                        }
                    }
                }
            } else {
                VStack(alignment: .leading, spacing: 7) {
                    nav("Estúdio", symbol: "slider.horizontal.3", route: "studio")
                    nav("Meu som", symbol: "waveform", route: "library")
                    nav("Conexão e IA", symbol: "link", route: "settings")
                    Button { showGuide = true } label: { Label("Guia de produção", systemImage: "book.closed").frame(maxWidth: .infinity, alignment: .leading).padding(11) }.buttonStyle(.plain).foregroundStyle(.secondary)
                }
            }
            Spacer()
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 7) {
                    Circle().fill(model.connected ? Color.green : Color.orange).frame(width: 5, height: 5)
                    Text(model.connected ? "Live conectado" : "Aguardando Live")
                }
                HStack(spacing: 7) {
                    Circle().fill(model.mcpReady ? Color.green : Color.orange).frame(width: 5, height: 5)
                    Text(model.mcpReady ? "Ferramentas conectadas" : "Preparando ferramentas")
                }
                Button("Meus dados", action: model.revealData).buttonStyle(.link).padding(.top, 5)
            }.font(.system(size: 11)).foregroundStyle(.secondary)
            Text("VERSÃO " + (Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "dev")).font(.system(size: 9, weight: .medium)).tracking(1.4).foregroundStyle(.tertiary)
        }.padding(22).frame(maxHeight: .infinity).background(Color.white.opacity(0.015))
    }
    private func nav(_ label: String, symbol: String, route: String) -> some View {
        Button { model.route = route; model.error = ""; model.message = "" } label: {
            Label(label, systemImage: symbol).font(.system(size: 13, weight: .medium))
                .frame(maxWidth: .infinity, alignment: .leading).padding(11)
                .background(model.route == route ? StudioStyle.accent.opacity(0.13) : Color.clear, in: RoundedRectangle(cornerRadius: 9))
        }.buttonStyle(.plain).foregroundStyle(model.route == route ? StudioStyle.accent : Color.secondary)
    }

    private var onboarding: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("CONFIGURAÇÃO GUIADA").font(.system(size: 10, weight: .semibold)).tracking(2).foregroundStyle(.secondary)
                Spacer()
                Text("\(model.step + 1) de \(stepNames.count)").font(.caption).foregroundStyle(.secondary)
            }.padding(.horizontal, 36).padding(.top, 34)
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    switch model.step {
                    case 0: welcome
                    case 1:
                        title("Vamos conectar ao Ableton", subtitle: "O app prepara o MCP automaticamente. A ponte do Live só precisa ser ativada uma vez.")
                        LiveSetupView(model: model)
                    case 2:
                        title("Mostre seus samples", subtitle: "Indexe as pastas com seus loops e one-shots. A IA passa a escolher sons seus por papel, tom e BPM. Opcional: dá para fazer depois.")
                        SamplesView(model: model)
                    case 3:
                        title("Escolha sua IA", subtitle: "Use o Claude Desktop que você já tem, ou converse com o ChatGPT dentro deste app.")
                        AssistantView(model: model)
                    case 4:
                        title("Ensine o seu som", subtitle: "Opcional. As referências mostram ao produtor o groove, os timbres e a estrutura que você procura. O primeiro aprendizado baixa os modelos de áudio.")
                        LearningView(model: model)
                    default: completion
                    }
                }.frame(maxWidth: 820, alignment: .leading).padding(36).frame(maxWidth: .infinity, alignment: .leading)
            }
            Divider().overlay(StudioStyle.line)
            HStack {
                if model.step > 0 { Button("Voltar", action: model.back).buttonStyle(.plain).foregroundStyle(.secondary) }
                Spacer()
                if model.busy { ProgressView().controlSize(.small) }
                Button(continueLabel, action: model.advance)
                    .buttonStyle(.borderedProminent).controlSize(.large).disabled(!model.canContinue)
            }.padding(.horizontal, 36).padding(.vertical, 22)
        }
    }
    private var continueLabel: String {
        if model.step == 0 { return "Configurar meu estúdio" }
        if model.step == AppModel.lastStep { return model.assistant == "claude" ? "Concluir" : "Entrar no estúdio" }
        if (model.step == 2 && model.sampleCount == 0) || (model.step == 4 && model.genres.isEmpty) { return "Pular por agora" }
        return "Continuar"
    }
    private var welcome: some View {
        VStack(alignment: .leading, spacing: 26) {
            Image(systemName: "waveform.path").font(.system(size: 64, weight: .light)).foregroundStyle(StudioStyle.accent).padding(.top, 24)
            Text("Seu novo parceiro\nde estúdio.").font(.system(size: 44, weight: .semibold)).tracking(-1.5)
            Text("Descreva o que você quer produzir. O app aprende com suas referências, entende o projeto no Ableton e transforma suas ideias em propostas que você pode ouvir e refinar.").font(.system(size: 16)).foregroundStyle(.secondary).lineSpacing(5)
            HStack(spacing: 14) {
                mini("Conecte", text: "Ableton, seus samples\ne o Claude em minutos.", icon: "link")
                mini("Ensine", text: "Faixas de referência\nmostram o seu som.", icon: "waveform")
                mini("Produza", text: "Converse com a IA, ouça\no resultado no Live.", icon: "sparkles")
            }.padding(.top, 8)
            Label("Leva uns 5 minutos. Tenha o Ableton Live aberto. Seus samples e o aprendizado ficam no seu Mac.", systemImage: "clock").font(.caption).foregroundStyle(.secondary)
        }
    }
    private func mini(_ title: String, text: String, icon: String) -> some View {
        Panel { Image(systemName: icon).foregroundStyle(StudioStyle.accent); Text(title).font(.headline); Text(text).font(.caption).foregroundStyle(.secondary) }
    }
    private var completion: some View {
        VStack(alignment: .leading, spacing: 24) {
            Image(systemName: "checkmark.circle.fill").font(.system(size: 52)).foregroundStyle(StudioStyle.accent)
            title("Seu estúdio está pronto", subtitle: model.assistant == "claude" ? "Agora é só conversar com o Claude, com o Live aberto. O Claude inicia as ferramentas sozinho: este app não precisa ficar aberto." : "Agora você pode produzir sem sair do app.")
            Panel {
                Label("Ableton e ferramentas locais conectados", systemImage: "checkmark")
                Label(model.sampleCount > 0 ? "\(model.sampleCount) samples indexados" : "Samples: indexe depois em Conexão e IA", systemImage: model.sampleCount > 0 ? "checkmark" : "circle.dashed")
                Label(model.genres.isEmpty ? "Nenhum gênero aprendido ainda (opcional)" : "\(model.genres.count) perfis musicais aprendidos", systemImage: model.genres.isEmpty ? "circle.dashed" : "checkmark")
                Label(model.assistant == "claude" ? "Assistente: Claude Desktop" : "Assistente: \(model.modelID)", systemImage: "checkmark")
            }
            if model.assistant == "claude" {
                ClaudeFirstPrompts()
            } else {
                Panel {
                Text("Seu primeiro ciclo").font(.headline)
                Text("1. Abra uma cópia do projeto no Ableton.\n2. Selecione o gênero de referência.\n3. Comece uma ideia de 4, 8 ou 16 compassos.\n4. Construa o loop, revise a proposta, aplique e ouça.\n5. Aprove o loop; desenvolva e aprove o groove.\n6. Abra o arranjo a partir do material aprovado.\n7. Compare um render e refine a próxima versão.").lineSpacing(9).foregroundStyle(.secondary)
                }
            }
        }
    }
    private var studioHeader: some View {
        HStack {
            VStack(alignment: .leading, spacing: 5) {
                Text(model.route == "studio" ? "Estúdio" : model.route == "library" ? "Meu som" : "Conexão e IA").font(.system(size: 22, weight: .semibold))
                Text(model.route == "studio" ? "Do seu prompt ao próximo take." : "Seu processo, sempre acessível.").font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            StatusPill(title: model.connected ? "Live online" : "Live offline", good: model.connected)
            StatusPill(title: model.mcpReady ? "MCP conectado" : "Reconectando MCP", good: model.mcpReady)
        }.padding(.horizontal, 28).padding(.vertical, 22).background(Color.white.opacity(0.01))
    }
    private var notices: some View {
        VStack(alignment: .leading, spacing: 7) {
            if !model.error.isEmpty { Label(model.error, systemImage: "exclamationmark.circle").foregroundStyle(.orange) }
            if !model.message.isEmpty { Label(model.message, systemImage: "checkmark.circle").foregroundStyle(.green) }
        }.font(.caption).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 28).padding(.vertical, model.error.isEmpty && model.message.isEmpty ? 0 : 13)
    }
    private func title(_ text: String, subtitle: String) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(text).font(.system(size: 29, weight: .semibold)).tracking(-0.5)
            Text(subtitle).font(.system(size: 14)).foregroundStyle(.secondary).lineSpacing(4)
        }
    }
}

struct LiveSetupView: View {
    @ObservedObject var model: AppModel
    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Panel {
                HStack {
                    Image(systemName: model.connected ? "checkmark.circle.fill" : "link").font(.system(size: 26)).foregroundStyle(model.connected ? Color.green : StudioStyle.accent)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(model.connected ? "Ableton encontrado" : "Conecte seu projeto").font(.headline)
                        Text(model.connected ? "\(model.tracks.count) faixas · \(model.song["tempo"] as? Double ?? 0, specifier: "%.0f") BPM" : "Abra o Live e ative a ponte seguindo o guia abaixo.").font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button("Verificar", action: model.refresh).disabled(!model.ready)
                }
                HStack {
                    Image(systemName: model.mcpReady ? "checkmark.circle" : "ellipsis.circle").foregroundStyle(model.mcpReady ? Color.green : Color.orange)
                    Text(model.mcpReady ? "Conexão MCP verificada · \(model.connection["tools"] as? Int ?? 0) ferramentas disponíveis" : "Preparando a conexão MCP dentro do app…").font(.callout).foregroundStyle(.secondary)
                }
            }
            if !model.connected {
                Panel {
                    Text("Ative a ponte uma vez").font(.headline)
                    Text("1. Clique em Preparar ponte abaixo.\n2. Feche o Ableton Live se ele estiver aberto (Cmd+Q) e abra de novo. O Live só encontra a ponte ao abrir.\n3. No Live, abra Settings → Link, Tempo & MIDI.\n4. Em Control Surface, escolha ClaudeBridge (é esse o nome na lista).\n5. Deixe Input e Output em None.").font(.callout).lineSpacing(8)
                    HStack {
                        Button("Preparar ponte", action: model.installBridge).buttonStyle(.borderedProminent).disabled(model.busy || !model.ready)
                        Button("Abrir Ableton", action: model.openLive)
                    }
                    Text("Esta tela muda automaticamente quando o Live responder. Se ClaudeBridge não aparecer na lista, confira em Biblioteca do Ableton (abaixo) se a User Library é a mesma de Live → Settings → Library, instale de novo e reabra o Live.").font(.caption).foregroundStyle(.secondary)
                }
            } else {
                Label("Tudo conectado. Você pode continuar para o aprendizado.", systemImage: "checkmark").foregroundStyle(.green).font(.callout)
            }
            DisclosureGroup("Biblioteca do Ableton e atualização da ponte") {
                VStack(alignment: .leading, spacing: 12) {
                    Text("A User Library é detectada pelas preferências do Live. Escolha outra pasta se sua biblioteca foi movida.").font(.caption).foregroundStyle(.secondary)
                    HStack { TextField("User Library", text: $model.userLibrary); Button("Escolher…") { model.chooseFolder(library: true) } }
                    Button("Instalar / atualizar ponte", action: model.installBridge).disabled(model.busy || !model.ready)
                    Text("Uma ponte já ativa é recarregada automaticamente. A primeira ativação da Control Surface acontece dentro do Live.").font(.caption).foregroundStyle(.secondary)
                }.padding(.top, 12)
            }.font(.callout)
        }
    }
}

struct LearningView: View {
    @ObservedObject var model: AppModel
    @State private var details = false
    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            if !model.genres.isEmpty {
                Panel {
                    Text("Seu som aprendido").font(.headline)
                    ForEach(Array(model.genres.enumerated()), id: \.offset) { _, genre in
                        HStack {
                            Image(systemName: "checkmark.circle.fill").foregroundStyle(StudioStyle.accent)
                            Text(genre["genre"] as? String ?? "").fontWeight(.medium)
                            Spacer(); Text("\(genre["n_tracks"] as? Int ?? 0) referências").font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
            }
            Panel {
                Text(model.genres.isEmpty ? "Monte seu primeiro gênero" : "Ensine um novo gênero").font(.headline)
                Text("Dê um nome ao estilo e adicione faixas que representem o som que você quer criar. O app organiza as referências para você.").font(.callout).foregroundStyle(.secondary)
                TextField("Nome do gênero · ex.: Indie Dance", text: $model.genreName).textFieldStyle(.roundedBorder).controlSize(.large)
                ForEach(Array(model.referenceFiles.enumerated()), id: \.offset) { index, file in
                    HStack {
                        Image(systemName: "music.note").foregroundStyle(StudioStyle.accent)
                        Text(URL(fileURLWithPath: file).lastPathComponent).font(.caption).lineLimit(1)
                        Spacer()
                        Button { model.referenceFiles.remove(at: index) } label: { Image(systemName: "xmark") }.buttonStyle(.plain).foregroundStyle(.secondary)
                    }
                }
                HStack {
                    Button("Adicionar faixas…", action: model.chooseReferences).disabled(model.training || model.busy)
                    Spacer()
                    Text("3–5 referências são um bom começo").font(.caption).foregroundStyle(.secondary)
                }
                if !model.preview.isEmpty {
                    Divider()
                    Text("Pasta pronta para aprender").font(.subheadline.weight(.medium))
                    ForEach(Array((model.preview["genres"] as? [[String: Any]] ?? []).enumerated()), id: \.offset) { _, genre in
                        HStack { Text(genre["genre"] as? String ?? ""); Spacer(); Text("\(genre["files"] as? Int ?? 0) faixas").foregroundStyle(.secondary) }.font(.caption)
                    }
                }
                HStack {
                    Button(model.training ? "Aprendizado em andamento" : "Aprender com minhas referências", action: model.train)
                        .buttonStyle(.borderedProminent).controlSize(.large)
                        .disabled(model.busy || model.training || !model.ready || (model.preview.isEmpty && (model.genreName.trimmingCharacters(in: .whitespaces).isEmpty || model.referenceFiles.isEmpty)))
                    if model.training || model.busy { ProgressView().controlSize(.small) }
                }
                Button("Já tenho uma pasta organizada por gêneros…") { model.chooseFolder() }.buttonStyle(.link).font(.caption).disabled(model.training)
            }.disabled(model.training)
            if !model.job.isEmpty, model.job["state"] != nil {
                Panel {
                    HStack {
                        if model.training { ProgressView().controlSize(.small) }
                        else { Image(systemName: "checkmark.circle").foregroundStyle(StudioStyle.accent) }
                        Text(model.trainingStage).font(.headline)
                    }
                    if let genre = model.job["current_genre"] as? String { Text("Aprendendo \(genre)").foregroundStyle(.secondary) }
                    let done = (model.job["completed"] as? [[String: Any]])?.count ?? 0
                    let total = (model.job["genres"] as? [String])?.count ?? 1
                    ProgressView(value: Double(done), total: Double(max(1, total))).tint(StudioStyle.accent)
                    Text("\(done) de \(total) gêneros salvos").font(.caption).foregroundStyle(.secondary)
                    Text("O app aprende ritmo e tonalidade, groove e dinâmica, timbres e estrutura. No primeiro uso, prepara os modelos de áudio; isso pode levar alguns minutos. Mantenha esta janela aberta e espere o aprendizado terminar antes de renderizar no Live.").font(.caption).foregroundStyle(.secondary).lineSpacing(4)
                    ForEach(Array((model.job["errors"] as? [[String: Any]] ?? []).enumerated()), id: \.offset) { _, item in
                        Text("\(item["genre"] as? String ?? ""): \(item["error"] as? String ?? "")").font(.caption).foregroundStyle(.orange)
                    }
                    DisclosureGroup("Detalhes da análise", isExpanded: $details) {
                        ForEach(Array((model.job["log"] as? [String] ?? []).enumerated()), id: \.offset) { _, line in
                            Text(line).font(.system(size: 10, design: .monospaced)).textSelection(.enabled)
                        }
                    }.font(.caption)
                }
            }
            Label("Os áudios originais ficam no lugar. Perfis e análises são salvos na sua biblioteca local.", systemImage: "externaldrive").font(.caption).foregroundStyle(.secondary)
        }
    }
}

struct AccountView: View {
    @ObservedObject var model: AppModel
    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Panel {
                Text("Use sua conta ChatGPT").font(.headline)
                Text("As respostas usam o plano ou os créditos elegíveis que você já tem na OpenAI. Os prompts, propostas e resultados ficam neste app.").font(.callout).foregroundStyle(.secondary)
                if model.accountConnected {
                    Label(model.accountEmail.isEmpty ? "Conta conectada" : model.accountEmail, systemImage: "checkmark.circle").foregroundStyle(.green).font(.callout)
                    Text("Usando seu plano ChatGPT").font(.caption).foregroundStyle(.secondary)
                }
                if !model.awaitingLogin {
                    Button("Continuar com ChatGPT") { model.connectAccount() }
                        .buttonStyle(.borderedProminent).controlSize(.large)
                        .disabled(model.busy || model.chatRunning || !model.proposals.isEmpty)
                } else {
                    HStack {
                        ProgressView().controlSize(.small)
                        Text("Aguardando seu login no navegador…").font(.callout)
                        Spacer()
                        Button("Cancelar", action: model.cancelLogin)
                    }
                }
                if let error = model.auth["error"] as? String { Text(error).font(.caption).foregroundStyle(.orange).textSelection(.enabled) }
                if !model.models.isEmpty {
                    Picker("Modelo", selection: $model.modelID) {
                        ForEach(model.models, id: \.self) { item in Text(item["name"] ?? item["id"] ?? "").tag(item["id"] ?? "") }
                    }.onChanged(model.modelID) { model.savePreferences(["provider": model.provider, "model": model.modelID]) }
                        .disabled(model.busy || model.chatRunning || !model.proposals.isEmpty)
                }
                if !model.proposals.isEmpty {
                    Text("Há uma proposta aguardando revisão. Aplique ou descarte a proposta no Estúdio para trocar o modelo.")
                        .font(.callout).foregroundStyle(.secondary)
                    Button("Revisar proposta no Estúdio") { model.route = "studio" }
                } else if model.chatRunning {
                    Text("Espere a resposta terminar para trocar o modelo.")
                        .font(.callout).foregroundStyle(.secondary)
                }
                if model.accountConnected {
                    HStack {
                        Button("Atualizar modelos", action: model.refreshModels)
                            .disabled(model.busy || model.chatRunning)
                        Button("Desconectar", action: model.disconnectAccount)
                            .disabled(model.busy || model.chatRunning || !model.proposals.isEmpty)
                        Spacer()
                        Link("Gerenciar uso", destination: URL(string: "https://chatgpt.com/#settings/Usage")!)
                    }.font(.caption)
                }
                let accounts = model.auth["accounts"] as? [[String: Any]] ?? []
                if !accounts.isEmpty {
                    DisclosureGroup("Contas e espaços salvos") {
                        ForEach(Array(accounts.enumerated()), id: \.offset) { index, account in
                            Button("\(account["label"] as? String ?? "Conta ChatGPT") · conexão \(index + 1)") { model.selectAccount(account["id"] as? String ?? "") }
                        }
                        Button("Adicionar outra conta ou espaço") { model.connectAccount(newAccount: true) }
                    }.font(.caption).disabled(model.busy || model.chatRunning || !model.proposals.isEmpty)
                }
                Divider()
                Text("O login e a autorização acontecem no site oficial da OpenAI. O app não recebe sua senha. Você controla o acesso e os limites nas configurações do ChatGPT. O uso é compartilhado com seu plano e depende da elegibilidade da conta.")
                    .font(.caption).foregroundStyle(.secondary).lineSpacing(4)
                Text("Ao enviar um prompt, a mensagem e as medições consultadas do projeto seguem para a OpenAI. Os arquivos de áudio são analisados no seu Mac.")
                    .font(.caption).foregroundStyle(.secondary).lineSpacing(4)
            }
            DisclosureGroup("Posso usar minha assinatura Claude?") {
                Text("Sim, pelo Claude Desktop: escolha Claude Desktop acima. O app registra as ferramentas no Claude Desktop e a conversa acontece lá, no seu plano Claude. O chat dentro deste app usa o login oficial da OpenAI.").font(.caption).foregroundStyle(.secondary).padding(.top, 8)
                Link("Regras oficiais da Anthropic", destination: URL(string: "https://code.claude.com/docs/en/agent-sdk/overview")!).font(.caption)
            }.font(.callout)
        }
    }
}

struct StudioView: View {
    @ObservedObject var model: AppModel
    @State private var loopBars = 8
    @State private var workingCopy = false
    @State private var workflowChoice = ""
    @State private var projectLabel = ""
    @State private var existingGoal = "diagnosis"
    @State private var savedProjectID = ""
    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    VStack(alignment: .leading, spacing: 5) {
                        Text("DIREÇÃO MUSICAL").font(.system(size: 9, weight: .semibold)).tracking(1.5).foregroundStyle(.secondary)
                        Picker("Gênero", selection: $model.activeGenre) {
                            ForEach(Array(model.genres.enumerated()), id: \.offset) { _, item in Text(item["genre"] as? String ?? "").tag(item["genre"] as? String ?? "") }
                        }.labelsHidden().frame(maxWidth: 240).onChanged(model.activeGenre) { model.savePreferences(["active_genre": model.activeGenre]) }
                    }
                    Spacer()
                    Button("Nova conversa", action: model.resetChat).font(.caption).disabled(model.chatRunning || model.busy)
                }
                if model.assistant == "claude" && !model.accountConnected {
                    Panel {
                        Label("Você está usando o Claude Desktop", systemImage: "bubble.left.and.text.bubble.right").font(.headline)
                        Text("Converse com o Claude: ele usa as ferramentas deste app para ler e mudar seu projeto no Live. O chat abaixo é para o ChatGPT (opcional, em Conexão e IA).").font(.callout).foregroundStyle(.secondary)
                        Button("Abrir o Claude Desktop", action: model.openClaude)
                    }
                }
                productionPanel
                chatPanel
            }.padding(26).frame(maxWidth: .infinity, maxHeight: .infinity)
            Rectangle().fill(StudioStyle.line).frame(width: 1)
            projectPanel.frame(width: 278)
        }
    }
    private var productionPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            if !model.hasProduction {
                Text("Como você quer trabalhar?").font(.headline)
                HStack {
                    Button { workflowChoice = "new"; workingCopy = false } label: { Label("Criar do zero", systemImage: "plus.circle").frame(maxWidth: .infinity) }
                        .tint(workflowChoice == "new" ? StudioStyle.accent : Color.secondary)
                    Button { workflowChoice = "existing"; workingCopy = false } label: { Label("Continuar projeto", systemImage: "waveform.path").frame(maxWidth: .infinity) }
                        .tint(workflowChoice == "existing" ? StudioStyle.accent : Color.secondary)
                }.buttonStyle(.bordered)
                if !workflowChoice.isEmpty {
                    Text(workflowChoice == "new" ? "Uma nova track: aprove um loop curto, desenvolva o groove e depois abra o arranjo." : "Uma track sua ou criada pelo app: preserve a identidade e melhore o que já existe, a partir do ponto atual.")
                        .font(.caption).foregroundStyle(.secondary)
                    TextField("Nome do projeto (opcional)", text: $projectLabel).textFieldStyle(.roundedBorder)
                    Toggle(workflowChoice == "new" ? "Estou num set vazio ou numa cópia" : "Abri uma cópia do projeto que quero editar", isOn: $workingCopy).font(.caption)
                    HStack {
                        if workflowChoice == "new" {
                            Picker("Loop", selection: $loopBars) { ForEach([4, 8, 16], id: \.self) { Text("\($0) compassos").tag($0) } }.frame(width: 180)
                        } else {
                            Picker("Objetivo", selection: $existingGoal) {
                                Text("Diagnóstico").tag("diagnosis"); Text("Groove").tag("groove")
                                Text("Arranjo").tag("arrangement"); Text("Mix").tag("mix")
                            }.frame(width: 210)
                        }
                        Spacer()
                        Button(workflowChoice == "new" ? "Começar ideia" : "Trabalhar neste projeto") {
                            if workflowChoice == "new" { model.beginIdea(bars: loopBars, confirmed: workingCopy, label: projectLabel) }
                            else { model.continueProject(label: projectLabel, goal: existingGoal, confirmed: workingCopy) }
                        }.buttonStyle(.borderedProminent)
                            .disabled(!workingCopy || !model.connected || !model.mcpReady || model.busy || model.chatRunning || !model.proposals.isEmpty)
                    }
                }
                if !model.productionProjects.isEmpty {
                    DisclosureGroup("Retomar projetos recentes salvos pelo app") {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Abra o projeto correspondente no Live. As etapas e aprovações são retomadas; o arquivo .als é aberto e salvo pelo Ableton.").font(.caption).foregroundStyle(.secondary)
                            Picker("Projeto", selection: $savedProjectID) {
                                Text("Selecione um projeto").tag("")
                                ForEach(Array(model.productionProjects.enumerated()), id: \.offset) { _, project in
                                    Text("\(project["label"] as? String ?? "Projeto") · \(projectStage(project))").tag(project["id"] as? String ?? "")
                                }
                            }
                            Button("O projeto correto está aberto · retomar") { model.restoreProject(savedProjectID) }
                                .disabled(savedProjectID.isEmpty || !model.connected || model.busy || model.chatRunning || !model.proposals.isEmpty)
                        }.padding(.top, 8)
                    }.font(.caption)
                }
            } else if model.productionNeedsResume {
                Text(model.production["label"] as? String ?? "Seu projeto").font(.headline)
                Text("Abra o mesmo projeto no Live para retomar o trabalho salvo.").font(.caption).foregroundStyle(.secondary)
                Button("O projeto correto está aberto · retomar") { model.productionAction("resume") }.disabled(model.busy || !model.connected)
                switchProject
            } else if model.existingProduction {
                Text(model.production["label"] as? String ?? "Projeto existente").font(.headline)
                Text("CONTINUAR PROJETO · \(projectStage(model.production))").font(.system(size: 10, weight: .semibold)).foregroundStyle(StudioStyle.accent)
                Text("Trabalhe no que já existe: diagnóstico, proposta, aplicação e escuta. Sem recomeçar pelo loop.").font(.caption).foregroundStyle(.secondary)
                HStack {
                    Button("\(model.production["goal"] as? String == "diagnosis" ? "Diagnosticar projeto" : "Propor melhoria")", action: model.improveProject).disabled(!model.canChat)
                    Button("Ouvir projeto") { model.transport("play") }.disabled(!model.connected)
                    Spacer()
                }.disabled(model.busy || model.chatRunning || !model.proposals.isEmpty || model.rendering)
                switchProject
            } else {
                Text(model.production["label"] as? String ?? "Sua ideia").font(.headline)
                HStack(spacing: 12) {
                    ForEach(Array([("loop", "1 · Loop"), ("groove", "2 · Groove"), ("arrangement", "3 · Arranjo")].enumerated()), id: \.offset) { _, stage in
                        let approved = (model.production["approvals"] as? [String] ?? []).contains(stage.0)
                        HStack(spacing: 5) {
                            if approved { Image(systemName: "checkmark.circle.fill") }
                            Text(stage.1)
                        }.font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(model.productionStage == stage.0 ? StudioStyle.accent : Color.secondary)
                        if stage.0 != "arrangement" { Image(systemName: "chevron.right").font(.caption2).foregroundStyle(.tertiary) }
                    }
                    Spacer()
                }
                let start = model.production["start_bar"] as? Int ?? 1
                let end = model.production["end_bar"] as? Int ?? 9
                Text(model.production["completed"] as? Bool == true ? "Arranjo aprovado. Continue ouvindo, comparando e refinando." :
                     model.productionStage == "loop" ? "Encontre o motivo e os timbres. Trecho \(start)–\(end), em faixas separadas." :
                     model.productionStage == "groove" ? "Seu loop foi aprovado. Agora faça a base respirar e ganhar movimento." :
                     "Seu groove foi aprovado. Agora conte a história em seções.").font(.caption).foregroundStyle(.secondary)
                HStack {
                    Button(model.productionStage == "loop" ? "Construir loop" : model.productionStage == "groove" ? "Desenvolver groove" : "Abrir arranjo") { model.developStage() }.disabled(!model.canChat)
                    Button("Ouvir \(model.productionLabel.lowercased())") { model.productionAction("audition") }.disabled(model.production["applied"] as? Bool != true || !model.connected)
                    Button(model.productionStage == "arrangement" ? "Ouvi e aprovo o arranjo" : "Ouvi e aprovo · avançar") { model.productionAction("approve") }.buttonStyle(.borderedProminent)
                        .disabled(model.production["auditioned"] as? Bool != true || model.production["completed"] as? Bool == true)
                    Spacer()
                }.disabled(model.busy || model.chatRunning || !model.proposals.isEmpty || model.rendering)
                HStack {
                    if model.productionStage != "loop" { Button("Voltar uma etapa") { model.productionAction("back") }.font(.caption) }
                    Spacer()
                }.disabled(model.busy || model.chatRunning || !model.proposals.isEmpty || model.rendering)
                switchProject
            }
        }.padding(15).background(StudioStyle.panel, in: RoundedRectangle(cornerRadius: 12))
    }
    private var switchProject: some View {
        HStack {
            Text("Salve o set no Live com ⌘S.").font(.caption).foregroundStyle(.secondary)
            Spacer()
            Button("Guardar e trocar de projeto") {
                model.productionAction("end"); workflowChoice = ""; workingCopy = false; projectLabel = ""; savedProjectID = ""
            }.font(.caption).disabled(model.busy || model.chatRunning || !model.proposals.isEmpty || model.rendering)
        }
    }
    private func projectStage(_ project: [String: Any]) -> String {
        if project["mode"] as? String == "existing" {
            return ["diagnosis": "Diagnóstico", "groove": "Groove", "arrangement": "Arranjo", "mix": "Mix"][project["goal"] as? String ?? "diagnosis"] ?? "Projeto existente"
        }
        return project["completed"] as? Bool == true ? "Arranjo aprovado" : ["loop": "Loop", "groove": "Groove", "arrangement": "Arranjo"][project["stage"] as? String ?? "loop"] ?? "Loop"
    }
    private var chatPanel: some View {
        VStack(alignment: .leading, spacing: 14) {
            ScrollViewReader { reader in
                ScrollView {
                    VStack(alignment: .leading, spacing: 21) {
                        if model.chatMessages.isEmpty {
                            VStack(alignment: .leading, spacing: 16) {
                                Image(systemName: "sparkles").font(.system(size: 27)).foregroundStyle(StudioStyle.accent)
                                Text(!model.hasProduction ? "Escolha seu ponto de partida" : model.guidedProduction ? "Vamos trabalhar o \(model.productionLabel.lowercased())" : "Vamos melhorar sua track").font(.system(size: 26, weight: .semibold))
                                Text("Peça com suas palavras. O produtor usa o projeto e o gênero aprendido para escolher os detalhes, propõe uma etapa e verifica o resultado com você.").font(.callout).foregroundStyle(.secondary).lineSpacing(4)
                                if model.guidedProduction {
                                    Button("Propor a primeira etapa") { model.developStage() }.buttonStyle(.borderedProminent).disabled(!model.canChat)
                                    starter("Quero outra variação", prompt: "Proponha uma variação da etapa atual, preservando a identidade da ideia e o intervalo curto. Não avance para outra etapa.")
                                } else if model.existingProduction {
                                starter("Deixe minha faixa mais profissional", prompt: "Deixe minha faixa mais profissional, preservando a identidade. Comece pela melhoria de maior impacto.")
                                starter("Melhore o groove", prompt: "Melhore o groove do meu projeto sem mudar sua identidade.")
                                starter("Dê mais impacto ao drop", prompt: "Dê mais impacto ao drop com contraste e uma transição bem cuidada.")
                                } else {
                                    Text("Crie uma track do zero, continue um projeto aberto no Live ou retome as etapas de uma ideia salva pelo app.").font(.caption).foregroundStyle(.secondary)
                                }
                            }.padding(.vertical, 28)
                        }
                        ForEach(Array(model.chatMessages.enumerated()), id: \.offset) { _, item in
                            let user = item["role"] as? String == "user"
                            VStack(alignment: .leading, spacing: 8) {
                                Text(user ? "VOCÊ" : "PRODUTOR").font(.system(size: 9, weight: .semibold)).tracking(1.6).foregroundStyle(user ? StudioStyle.accent : Color.secondary)
                                Text(.init(item["text"] as? String ?? "")).font(.system(size: 14)).lineSpacing(5).textSelection(.enabled)
                            }.frame(maxWidth: .infinity, alignment: .leading).padding(user ? 16 : 2)
                                .background(user ? StudioStyle.accent.opacity(0.08) : Color.clear, in: RoundedRectangle(cornerRadius: 12))
                        }
                        if let partial = model.chat["partial"] as? String, !partial.isEmpty {
                            Text(.init(partial)).font(.system(size: 14)).lineSpacing(5).textSelection(.enabled)
                        }
                        if model.chatRunning {
                            HStack(spacing: 10) { ProgressView().controlSize(.small); Text((model.chat["events"] as? [String])?.last ?? "O produtor está trabalhando…").font(.caption).foregroundStyle(.secondary) }
                        }
                        if let error = model.chat["error"] as? String { Label(error, systemImage: "exclamationmark.circle").font(.callout).foregroundStyle(.orange) }
                        if let execution = model.chat["execution"] as? [[String: Any]], !execution.isEmpty {
                            executionReceipt(execution)
                        }
                        if !model.proposals.isEmpty { proposal }
                        Color.clear.frame(height: 1).id("bottom")
                    }.padding(.horizontal, 3)
                }.onChanged(model.chatMessages.count) { withAnimation { reader.scrollTo("bottom", anchor: .bottom) } }
                    .onChanged(model.proposals.count) { withAnimation { reader.scrollTo("bottom", anchor: .bottom) } }
            }
            if let events = model.chat["events"] as? [String], !events.isEmpty {
                DisclosureGroup("Atividade da sessão") { ForEach(Array(events.enumerated()), id: \.offset) { _, event in Text(event).font(.caption).foregroundStyle(.secondary) } }.font(.caption).foregroundStyle(.secondary)
            }
            if let efficiency = model.chat["efficiency"] as? [String: Any], let requests = efficiency["requests"] as? Int, requests > 0 {
                DisclosureGroup("Uso deste pedido · \(requests) chamadas") {
                    if let input = efficiency["input_tokens"] as? Int, let output = efficiency["output_tokens"] as? Int {
                        Text("\(input) tokens de entrada · \(output) de saída").font(.caption)
                    } else { Text("O modelo não informou a contagem de tokens.").font(.caption) }
                    Text("Ferramentas carregadas conforme a tarefa. Material MIDI reutilizado localmente.").font(.caption)
                }.font(.caption).foregroundStyle(.secondary)
            }
            VStack(alignment: .leading, spacing: 12) {
                ZStack(alignment: .topLeading) {
                    if model.draft.isEmpty { Text("Descreva sua ideia, ajuste ou objetivo…").foregroundStyle(.tertiary).padding(.top, 8).padding(.leading, 5).allowsHitTesting(false) }
                    TextEditor(text: $model.draft).font(.system(size: 14)).scrollContentBackground(.hidden).frame(minHeight: 65, maxHeight: 100)
                }
                HStack {
                    Text(model.accountConnected ? "Plano ChatGPT · \(model.modelID)" : "Conecte sua conta em Conexão e IA").font(.system(size: 10)).foregroundStyle(.secondary).lineLimit(1)
                    if model.accountConnected { Link("Gerenciar uso", destination: URL(string: "https://chatgpt.com/#settings/Usage")!).font(.system(size: 10)) }
                    Spacer()
                    Button { model.send() } label: { Label("Enviar", systemImage: "arrow.up") }
                        .buttonStyle(.borderedProminent).keyboardShortcut(.return, modifiers: .command)
                        .disabled(!model.canChat || model.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }.padding(15).background(StudioStyle.panel, in: RoundedRectangle(cornerRadius: 13))
                .overlay(RoundedRectangle(cornerRadius: 13).stroke(StudioStyle.line))
        }.frame(maxWidth: .infinity, maxHeight: .infinity)
    }
    private func starter(_ title: String, prompt: String) -> some View {
        Button { model.send(prompt) } label: {
            HStack { Text(title); Spacer(); Image(systemName: "arrow.up.right").font(.caption) }
                .padding(13).background(StudioStyle.panel, in: RoundedRectangle(cornerRadius: 10))
        }.buttonStyle(.plain).disabled(!model.canChat)
    }
    private var proposal: some View {
        Panel {
            Label("Proposta para revisar", systemImage: "slider.horizontal.3").font(.headline)
            let count = model.proposals.reduce(0) { $0 + (($1["preview"] as? [[String: Any]])?.count ?? 1) }
            Text("\(count) ações aguardam sua revisão. Confira a intenção musical na resposta do produtor e os detalhes abaixo.").font(.caption).foregroundStyle(.secondary)
            ForEach(Array(model.proposals.enumerated()), id: \.offset) { _, item in
                VStack(alignment: .leading, spacing: 6) {
                    if let preview = item["preview"] as? [[String: Any]], !preview.isEmpty {
                        ForEach(Array(preview.enumerated()), id: \.offset) { _, action in
                            Text(action["title"] as? String ?? "Ação no Live").font(.callout.weight(.medium))
                            if let detail = action["detail"] as? String, !detail.isEmpty {
                                Text(detail).font(.caption).foregroundStyle(.secondary).textSelection(.enabled)
                            }
                        }
                    } else { Text(actionTitle(item)).font(.callout.weight(.medium)) }
                    DisclosureGroup("Ver parâmetros") {
                        Text(json(item["args"] ?? [:])).font(.system(size: 10, design: .monospaced)).textSelection(.enabled)
                    }.font(.caption).foregroundStyle(.secondary)
                }
            }
            HStack {
                Button("Aplicar proposta") { model.send(approve: true) }.buttonStyle(.borderedProminent).disabled(!model.connected || model.training)
                Button("Descartar") { model.send(approve: false) }
            }.disabled(model.busy || model.chatRunning)
        }
    }
    private func executionReceipt(_ items: [[String: Any]]) -> some View {
        Panel {
            Label("Resultado da execução", systemImage: "checklist").font(.headline)
            ForEach(Array(items.enumerated()), id: \.offset) { _, item in
                let status = item["status"] as? String ?? "failed"
                let label = status == "applied" ? "Aplicada" : status == "skipped" ? "Não executada" : "Falhou"
                VStack(alignment: .leading, spacing: 4) {
                    Label("\(label) · \(item["title"] as? String ?? "Ação")", systemImage: status == "applied" ? "checkmark.circle" : "exclamationmark.circle")
                        .font(.caption.weight(.medium)).foregroundStyle(status == "applied" ? Color.secondary : Color.orange)
                    if let error = item["error"] as? String { Text(error).font(.caption).foregroundStyle(.orange).textSelection(.enabled) }
                    if let detail = item["detail"] as? String, !detail.isEmpty { Text(detail).font(.caption).foregroundStyle(.secondary).textSelection(.enabled) }
                    if let id = item["change_id"] { Text("Registro para reversão: \(String(describing: id))").font(.caption2).foregroundStyle(.secondary) }
                }
            }
            Text("Execução confirmada pelas ferramentas. A qualidade musical precisa de escuta e comparação do áudio.").font(.caption).foregroundStyle(.secondary)
        }
    }
    private func actionTitle(_ item: [String: Any]) -> String {
        let name = item["name"] as? String ?? ""
        let args = item["args"] as? [String: Any] ?? [:]
        let labels = ["create_midi_clip": "Criar parte MIDI", "create_audio_clip": "Adicionar áudio", "set_param": "Ajustar processamento",
                      "set_track": "Ajustar faixa", "set_tempo": "Ajustar tempo", "transport": "Controlar reprodução",
                      "load_device": "Carregar instrumento ou efeito", "delete_track": "Remover faixa", "delete_clip": "Remover clip",
                      "set_cue": "Marcar seção", "fill_range": "Desenvolver arranjo", "set_clip": "Ajustar clip"]
        if name == "ableton_command" { return labels[args["cmd"] as? String ?? ""] ?? "Editar projeto no Ableton" }
        return ["render_start": "Renderizar trecho", "mix_toward_genre": "Aproximar mix das referências", "live_undo": "Desfazer no Live",
                "revert_changes": "Reverter ajustes", "groove_loop": "Criar loop com o groove aprendido"][name] ?? "Executar etapa de produção"
    }
    private func json(_ value: Any) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys]) else { return "" }
        return String(data: data, encoding: .utf8) ?? ""
    }
    private var projectPanel: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 23) {
                HStack {
                    Text("PROJETO NO LIVE").font(.system(size: 10, weight: .semibold)).tracking(1.3).foregroundStyle(.secondary)
                    Spacer(); Button(action: model.refresh) { Image(systemName: "arrow.clockwise") }.buttonStyle(.plain)
                }
                HStack(alignment: .firstTextBaseline, spacing: 6) {
                    Text("\(model.song["tempo"] as? Double ?? 0, specifier: "%.1f")").font(.system(size: 34, weight: .light, design: .rounded))
                    Text("BPM").font(.caption).foregroundStyle(.secondary)
                    Spacer(); Text(model.song["signature"] as? String ?? "—").font(.callout).foregroundStyle(.secondary)
                }
                HStack(spacing: 12) {
                    Button { model.transport("play") } label: { Image(systemName: "play.fill") }
                    Button { model.transport("stop") } label: { Image(systemName: "stop.fill") }
                    Text(model.song["is_playing"] as? Bool == true ? "Tocando" : "Parado").font(.caption).foregroundStyle(.secondary)
                }.disabled(!model.connected || model.busy || model.rendering)
                Divider()
                Text("\(model.tracks.count) FAIXAS").font(.system(size: 10, weight: .semibold)).tracking(1.2).foregroundStyle(.secondary)
                ForEach(Array(model.tracks.enumerated()), id: \.offset) { _, track in
                    Button { model.inspect(track) } label: {
                        HStack(alignment: .top, spacing: 9) {
                            Image(systemName: track["kind"] as? String == "midi" ? "pianokeys" : "waveform").foregroundStyle(StudioStyle.accent).frame(width: 18)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(track["name"] as? String ?? "").font(.system(size: 12, weight: .medium)).lineLimit(1)
                                Text("\(track["clips_active"] as? Int ?? 0) clips · \((track["devices"] as? [String] ?? []).prefix(2).joined(separator: ", "))").font(.system(size: 10)).foregroundStyle(.secondary).lineLimit(1)
                            }
                        }.frame(maxWidth: .infinity, alignment: .leading)
                    }.buttonStyle(.plain).disabled(model.busy || !model.connected)
                }
                if !model.selectedTrack.isEmpty {
                    Divider()
                    Text(model.selectedTrack["name"] as? String ?? "Faixa selecionada").font(.headline)
                    ForEach(Array((model.selectedTrack["devices"] as? [[String: Any]] ?? []).enumerated()), id: \.offset) { _, device in
                        Text(device["name"] as? String ?? "").font(.caption).foregroundStyle(.secondary)
                    }
                }
                Divider()
                Text("OUVIR E COMPARAR").font(.system(size: 10, weight: .semibold)).tracking(1.2).foregroundStyle(.secondary)
                HStack { TextField("Início", text: $model.renderStart); Text("→").foregroundStyle(.secondary); TextField("Fim", text: $model.renderEnd) }.textFieldStyle(.roundedBorder)
                Text("Intervalo em compassos. O render dura o tempo real do trecho.").font(.system(size: 10)).foregroundStyle(.secondary)
                Button(model.rendering ? "Renderizando…" : "Renderizar trecho", action: model.startRender)
                    .disabled(!model.connected || model.busy || model.training || model.rendering)
                if model.rendering { ProgressView().controlSize(.small); Text("Aguarde a captura do áudio terminar.").font(.caption).foregroundStyle(.secondary) }
                if let file = model.render["file"] as? String, model.render["state"] as? String == "done" {
                    Button("Comparar último render") { model.analyze(file) }.disabled(model.busy || model.training)
                }
                Button("Analisar arquivo…", action: model.chooseAnalysis).disabled(model.busy || model.rendering || model.training)
                if !model.report.isEmpty {
                    let loudness = model.report["loudness"] as? [String: Any] ?? [:]
                    Text(URL(fileURLWithPath: model.reportFile).lastPathComponent).font(.caption.weight(.medium)).lineLimit(2)
                    metric("Loudness", value: loudness["integrated_lufs"], unit: "LUFS")
                    metric("True peak", value: loudness["true_peak_dbtp"], unit: "dBTP")
                    metric("Dinâmica", value: loudness["crest_db"], unit: "dB")
                    Text("\((model.report["eq_moves"] as? [Any] ?? []).count) bandas fora da faixa típica das referências.").font(.caption).foregroundStyle(.secondary)
                    Button("Pedir diagnóstico no chat") { model.send("Interprete a comparação do áudio \(model.reportFile) com o gênero \(model.activeGenre). Explique em português as três prioridades da mix, usando as medições. Não aplique mudanças ainda.") }.font(.caption).disabled(!model.canChat)
                }
            }.padding(22)
        }.background(Color.white.opacity(0.015))
    }
    private func metric(_ label: String, value: Any?, unit: String) -> some View {
        HStack {
            Text(label).foregroundStyle(.secondary); Spacer()
            if let number = value as? Double { Text("\(number, specifier: "%.1f") \(unit)") }
            else { Text(value as? String ?? "—") }
        }.font(.caption)
    }
}

@main
struct AbletonClaudeApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var delegate
    @StateObject private var model = AppModel()
    var body: some Scene {
        WindowGroup { ContentView(model: model).onAppear { delegate.model = model } }
            .defaultSize(width: 1210, height: 840)
            .commands { CommandGroup(replacing: .newItem) {} }
    }
}

struct SamplesView: View {
    @ObservedObject var model: AppModel
    var body: some View {
        Panel {
            HStack {
                Image(systemName: model.sampleCount > 0 ? "checkmark.circle.fill" : "folder.badge.plus").font(.system(size: 24)).foregroundStyle(model.sampleCount > 0 ? Color.green : StudioStyle.accent)
                VStack(alignment: .leading, spacing: 4) {
                    Text(model.sampleCount > 0 ? "\(model.sampleCount) samples indexados" : "Suas pastas de samples").font(.headline)
                    Text(model.sampleFolders.isEmpty ? "Escolha uma ou mais pastas: packs, Splice, sua coleção. Os arquivos não são copiados nem enviados." : model.sampleFolders.map { ($0 as NSString).lastPathComponent }.joined(separator: " · ")).font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                Button(model.sampleCount > 0 ? "Trocar pastas…" : "Escolher pastas…", action: model.chooseSamples).buttonStyle(.borderedProminent).disabled(model.busy || !model.ready)
            }
            if model.busy { HStack { ProgressView().controlSize(.small); Text("Lendo nomes e cabeçalhos dos arquivos…").font(.caption).foregroundStyle(.secondary) } }
            Text("A indexação lê só nomes e cabeçalhos (rápido). O tom e o BPM vêm do nome do arquivo quando existem. Indexar de novo substitui as pastas anteriores.").font(.caption).foregroundStyle(.secondary)
        }
    }
}

struct ClaudeFirstPrompts: View {
    var body: some View {
        Panel {
            Text("Primeiras mensagens para o Claude").font(.headline)
            Text("Abra um set vazio ou uma cópia do seu projeto no Live e experimente:").font(.callout).foregroundStyle(.secondary)
            ForEach(["Veja o status do meu projeto no Ableton e me diga o que tem nele.",
                     "Procure nos meus samples um kick e um hat que combinem com house a 124 BPM.",
                     "Monte um loop de 8 compassos com meus samples e um baixo em Lá menor.",
                     "Renderize os compassos 1 a 9 e me diga o que melhorar na mix."], id: \.self) { prompt in
                HStack {
                    Text("“\(prompt)”").font(.callout).textSelection(.enabled)
                    Spacer()
                    Button { NSPasteboard.general.clearContents(); NSPasteboard.general.setString(prompt, forType: .string) } label: { Image(systemName: "doc.on.doc") }.buttonStyle(.plain).help("Copiar")
                }
            }
            Text("O Claude pede permissão na primeira vez que usa cada ferramenta. Salve no Live com ⌘S: a IA não salva por você.").font(.caption).foregroundStyle(.secondary)
        }
    }
}

struct AssistantView: View {
    @ObservedObject var model: AppModel
    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack(spacing: 14) {
                choice("claude", title: "Claude Desktop", text: "Use seu plano Claude. Você conversa no app do Claude; este app faz a ponte com o Live.", icon: "bubble.left.and.text.bubble.right")
                choice("chatgpt", title: "ChatGPT no app", text: "Entre com sua conta ChatGPT e converse dentro deste app.", icon: "sparkles")
            }
            if model.assistant == "claude" {
                Panel {
                    step(1, done: model.claudeInstalled, title: model.claudeInstalled ? "Claude Desktop instalado" : "Instale o Claude Desktop") {
                        if !model.claudeInstalled { Link("Baixar em claude.ai/download", destination: URL(string: "https://claude.ai/download")!).font(.callout) }
                    }
                    step(2, done: model.claudeConfigured, title: model.claudeConfigured ? "Ferramentas registradas no Claude" : "Registre as ferramentas no Claude") {
                        Button(model.claudeConfigured ? "Registrar de novo" : "Conectar ao Claude Desktop", action: model.configureClaude)
                            .buttonStyle(.borderedProminent).disabled(model.busy || !model.ready)
                    }
                    step(3, done: false, title: "Reabra o Claude para carregar as ferramentas") {
                        Button("Reabrir o Claude Desktop", action: model.restartClaude).disabled(!model.claudeConfigured)
                    }
                    Text("A configuração existente do Claude é preservada, com backup. As ferramentas aparecem como ableton-claude no menu de conectores do chat.").font(.caption).foregroundStyle(.secondary)
                }
            } else if model.assistant == "chatgpt" {
                AccountView(model: model)
            }
        }
    }
    private func choice(_ name: String, title: String, text: String, icon: String) -> some View {
        Button { model.chooseAssistant(name) } label: {
            VStack(alignment: .leading, spacing: 8) {
                Image(systemName: icon).font(.system(size: 20)).foregroundStyle(StudioStyle.accent)
                Text(title).font(.headline)
                Text(text).font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }.padding(16).frame(maxWidth: .infinity, minHeight: 120, alignment: .topLeading)
                .background(model.assistant == name ? StudioStyle.accent.opacity(0.13) : Color.white.opacity(0.03), in: RoundedRectangle(cornerRadius: 12))
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(model.assistant == name ? StudioStyle.accent : StudioStyle.line, lineWidth: 1))
        }.buttonStyle(.plain)
    }
    private func step<Action: View>(_ n: Int, done: Bool, title: String, @ViewBuilder action: () -> Action) -> some View {
        HStack(spacing: 12) {
            ZStack {
                Circle().fill(done ? Color.green.opacity(0.18) : Color.white.opacity(0.05)).frame(width: 26, height: 26)
                if done { Image(systemName: "checkmark").font(.system(size: 11, weight: .bold)).foregroundStyle(.green) }
                else { Text(String(n)).font(.system(size: 12, weight: .semibold)) }
            }
            Text(title).font(.callout)
            Spacer()
            action()
        }
    }
}

extension View {
    /// onChange that also builds for macOS 13 (Intel Ventura); the two-argument form is macOS 14+.
    @ViewBuilder func onChanged<V: Equatable>(_ value: V, _ action: @escaping () -> Void) -> some View {
        if #available(macOS 14.0, *) { onChange(of: value) { action() } }
        else { onChange(of: value) { _ in action() } }
    }
}
