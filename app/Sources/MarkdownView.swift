import SwiftUI

struct MarkdownChunk: Identifiable {
    let id = UUID()
    let type: ChunkType
    
    enum ChunkType {
        case text(AttributedString)
        case code(String, language: String?)
    }
}

struct MarkdownContentView: View {
    let content: String
    var isUser: Bool = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            ForEach(parse(content)) { chunk in
                switch chunk.type {
                case .text(let attributed):
                    Text(attributed)
                        .font(.system(size: 13))
                        .lineSpacing(3)
                        .textSelection(.enabled)
                        .foregroundColor(isUser ? .white : .primary.opacity(0.9))
                        .fixedSize(horizontal: false, vertical: false)
                case .code(let code, let lang):
                    CodeBlockView(code: code, language: lang, isUser: isUser)
                }
            }
        }
    }
    
    private func parse(_ text: String) -> [MarkdownChunk] {
        var chunks: [MarkdownChunk] = []
        let lines = text.components(separatedBy: .newlines)
        
        var currentText = ""
        var currentCode = ""
        var currentLang: String? = nil
        var isInsideCodeBlock = false
        
        for line in lines {
            if line.trimmed.hasPrefix("```") {
                if isInsideCodeBlock {
                    // Ending code block
                    if !currentCode.isEmpty {
                        chunks.append(MarkdownChunk(type: .code(currentCode.trimmingCharacters(in: .newlines), language: currentLang)))
                    }
                    currentCode = ""
                    currentLang = nil
                    isInsideCodeBlock = false
                } else {
                    // Starting code block
                    if !currentText.trimmed.isEmpty {
                        chunks.append(MarkdownChunk(type: .text(parseMarkdown(currentText.trimmed))))
                    }
                    currentText = ""
                    
                    // Extract language
                    let lang = line.trimmed.replacingOccurrences(of: "```", with: "").trimmed
                    currentLang = lang.isEmpty ? nil : lang
                    isInsideCodeBlock = true
                }
            } else {
                if isInsideCodeBlock {
                    currentCode += line + "\n"
                } else {
                    currentText += line + "\n"
                }
            }
        }
        
        if !currentText.trimmed.isEmpty {
            chunks.append(MarkdownChunk(type: .text(parseMarkdown(currentText.trimmed))))
        }
        
        if isInsideCodeBlock && !currentCode.trimmed.isEmpty {
            chunks.append(MarkdownChunk(type: .code(currentCode.trimmingCharacters(in: .newlines), language: currentLang)))
        }
        
        return chunks
    }
    
    private func parseMarkdown(_ text: String) -> AttributedString {
        do {
            var options = AttributedString.MarkdownParsingOptions()
            options.interpretedSyntax = .inlineOnlyPreservingWhitespace
            return try AttributedString(markdown: text, options: options)
        } catch {
            return AttributedString(text)
        }
    }
}

struct CodeBlockView: View {
    let code: String
    let language: String?
    var isUser: Bool = false
    @State private var copied = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            HStack {
                HStack(spacing: 6) {
                    Image(systemName: "terminal.fill")
                        .font(.system(size: 10))
                    if let language = language {
                        Text(language.uppercased())
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                    }
                }
                .foregroundColor(isUser ? .white.opacity(0.7) : .secondary)
                
                Spacer()
                
                Button(action: copyToClipboard) {
                    HStack(spacing: 4) {
                        Image(systemName: copied ? "checkmark" : "doc.on.doc")
                        Text(copied ? "Copied" : "Copy")
                    }
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(copied ? .green : (isUser ? .white.opacity(0.7) : .secondary))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(isUser ? Color.white.opacity(0.1) : Color.primary.opacity(0.05))
            
            // Content
            ScrollView(.horizontal, showsIndicators: false) {
                Text(code)
                    .font(.system(size: 12, design: .monospaced))
                    .padding(12)
                    .textSelection(.enabled)
                    .foregroundColor(isUser ? .white : .primary.opacity(0.9))
            }
            .background(isUser ? Color.black.opacity(0.1) : Color.primary.opacity(0.02))
        }
        .background(isUser ? Color.black.opacity(0.05) : Color.clear)
        .cornerRadius(8)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(isUser ? Color.white.opacity(0.2) : Color.primary.opacity(0.1), lineWidth: 1)
        )
        .padding(.vertical, 4)
    }
    
    private func copyToClipboard() {
        #if os(macOS)
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(code, forType: .string)
        #else
        UIPasteboard.general.string = code
        #endif
        
        withAnimation { copied = true }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            withAnimation { copied = false }
        }
    }
}

extension String {
    var trimmed: String {
        self.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
