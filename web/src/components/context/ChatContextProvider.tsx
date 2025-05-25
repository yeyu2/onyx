"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useChatContext, ChatProvider } from "./ChatContext";
import { ChatSession, InputPrompt } from "@/app/chat/interfaces";
import { CCPairBasicInfo, DocumentSet, Tag, ValidSources } from "@/lib/types";
import { LLMProviderDescriptor } from "@/app/admin/configuration/llm/interfaces";
import { Folder } from "@/app/chat/folders/interfaces";
import { useAvailableDatasets } from "@/app/admin/documents/datasets/hooks";

export const ChatContextProvider = ({
  children,
  chatSessions = [],
  availableSources = [],
  documentSets = [],
  tags = [],
  ccPairs = [],
  llmProviders = [],
  folders = [],
  openedFolders = {},
  sidebarInitiallyVisible = true,
  shouldShowWelcomeModal = false,
  shouldDisplaySourcesIncompleteModal = false,
  defaultAssistantId,
  inputPrompts = [],
  proSearchToggled = false,
  availableDatasets = [],
}: {
  children: React.ReactNode;
  chatSessions?: ChatSession[];
  availableSources?: ValidSources[];
  documentSets?: DocumentSet[];
  tags?: Tag[];
  ccPairs?: CCPairBasicInfo[];
  llmProviders?: LLMProviderDescriptor[];
  folders?: Folder[];
  openedFolders?: Record<string, boolean>;
  sidebarInitiallyVisible?: boolean;
  shouldShowWelcomeModal?: boolean;
  shouldDisplaySourcesIncompleteModal?: boolean;
  defaultAssistantId?: number;
  inputPrompts?: InputPrompt[];
  proSearchToggled?: boolean;
  availableDatasets?: { id: number; name: string }[];
}) => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [updatedChatSessions, setUpdatedChatSessions] = useState(chatSessions);
  const [updatedFolders, setUpdatedFolders] = useState(folders);
  const [updatedInputPrompts, setUpdatedInputPrompts] = useState(inputPrompts);
  
  // Fetch available datasets using the hook
  const { datasets: fetchedDatasets, loading: datasetsLoading } = useAvailableDatasets();
  
  // Use passed datasets or fetched datasets if none are passed
  const datasets = availableDatasets?.length ? availableDatasets : fetchedDatasets;

  const refreshChatSessions = async () => {
    try {
      const response = await fetch("/api/chat/get-user-chat-sessions");
      if (!response.ok) throw new Error("Failed to fetch chat sessions");
      const { sessions } = await response.json();
      setUpdatedChatSessions(sessions);

      const currentSessionId = searchParams?.get("chatId");
      if (
        currentSessionId &&
        !sessions.some(
          (session: ChatSession) => session.id === currentSessionId
        )
      ) {
        router.replace("/chat");
      }
    } catch (error) {
      console.error("Error refreshing chat sessions:", error);
    }
  };

  const reorderFolders = (displayPriorityMap: Record<number, number>) => {
    setUpdatedFolders(
      updatedFolders.map((folder) => {
        if (folder.folder_id) {
          const display_priority = displayPriorityMap[folder.folder_id];
          if (display_priority !== undefined) {
            folder.display_priority = display_priority;
          }
        }
        return folder;
      })
    );
  };

  const refreshFolders = async () => {
    const response = await fetch("/api/folder");
    if (!response.ok) throw new Error("Failed to fetch folders");
    const { folders } = await response.json();
    setUpdatedFolders(folders);
  };

  const refreshInputPrompts = async () => {
    const response = await fetch("/api/input_prompt");
    if (!response.ok) throw new Error("Failed to fetch input prompts");
    const inputPrompts = await response.json();
    setUpdatedInputPrompts(inputPrompts);
  };

  return (
    <ChatProvider
      value={{
        chatSessions: updatedChatSessions,
        availableSources,
        tags,
        documentSets,
        availableDocumentSets: documentSets,
        availableTags: tags,
        ccPairs,
        llmProviders,
        folders: updatedFolders,
        openedFolders,
        sidebarInitiallyVisible,
        shouldShowWelcomeModal,
        shouldDisplaySourcesIncompleteModal,
        defaultAssistantId,
        inputPrompts: updatedInputPrompts,
        proSearchToggled,
        availableDatasets: datasets,
      }}
    >
      {children}
    </ChatProvider>
  );
}; 