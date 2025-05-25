"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import { DatabaseIcon } from "@/components/icons/icons";
import { DatasetCreationForm } from "../DatasetCreationForm";
import { useConnectorStatus, useUserGroups } from "@/lib/hooks";
import { ThreeDotsLoader } from "@/components/Loading";
import { usePopup } from "@/components/admin/connectors/Popup";
import { BackButton } from "@/components/BackButton";
import { ErrorCallout } from "@/components/ErrorCallout";
import { useRouter } from "next/navigation";
import { refreshDatasets } from "../hooks";
import CardSection from "@/components/admin/CardSection";

function Main() {
  const { popup, setPopup } = usePopup();
  const router = useRouter();

  const {
    data: ccPairs,
    isLoading: isCCPairsLoading,
    error: ccPairsError,
  } = useConnectorStatus();

  // EE only
  const { data: userGroups, isLoading: userGroupsIsLoading } = useUserGroups();

  if (isCCPairsLoading || userGroupsIsLoading) {
    return <ThreeDotsLoader />;
  }

  if (ccPairsError || !ccPairs) {
    return (
      <ErrorCallout
        errorTitle="Failed to fetch Connectors"
        errorMsg={ccPairsError}
      />
    );
  }

  return (
    <>
      {popup}

      <CardSection>
        <DatasetCreationForm
          ccPairs={ccPairs}
          userGroups={userGroups}
          onClose={() => {
            refreshDatasets();
            router.push("/admin/documents/datasets");
          }}
          setPopup={setPopup}
        />
      </CardSection>
    </>
  );
}

export default function Page() {
  return (
    <div>
      <BackButton />
      <AdminPageTitle
        icon={<DatabaseIcon size={32} />}
        title="Create New Dataset"
      />

      <Main />
    </div>
  );
} 